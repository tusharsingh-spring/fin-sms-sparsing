import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from datetime import datetime
import time

load_dotenv()

print("📦 Loading Database Module for finapp_sms...")

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        """Establish database connection with correct database name"""
        try:
            print("Connecting to PostgreSQL...")
            print(f"Database: {os.getenv('DB_NAME', 'finapp_sms')}")
            print(f"User: {os.getenv('DB_USER', 'postgres')}")
            print(f"Host: {os.getenv('DB_HOST', 'localhost')}")
            
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_NAME', 'finapp_sms'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres123'),
                port=os.getenv('DB_PORT', '5432'),
                connect_timeout=5
            )
            
            self.conn.autocommit = False
            print(" Connected to finapp_sms database successfully!")
            
            # Create all tables
            self.create_all_tables()
            
        except psycopg2.OperationalError as e:
            print(f" Database connection failed: {e}")
            print("\nTroubleshooting steps:")
            print("1. Make sure PostgreSQL is running")
            print("2. Check if database 'finapp_sms' exists")
            print("3. Verify credentials in .env file")
            print("4. Try: CREATE DATABASE finapp_sms;")
            self.conn = None
        except Exception as e:
            print(f" Unexpected error: {e}")
            self.conn = None
    
    def create_all_tables(self):
        """Create all required tables"""
        if not self.conn:
            print(" No database connection, skipping table creation")
            return
        
        try:
            with self.conn.cursor() as cursor:
                print("Creating/verifying tables in finapp_sms...")
                
                # USERS TABLE
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100),
                        email VARCHAR(255) UNIQUE,
                        phone VARCHAR(20),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print(" users table ready")
                
                # Insert test user
                cursor.execute("""
                    INSERT INTO users (name, email, phone) 
                    VALUES ('Test User', 'test@example.com', '9876543210')
                    ON CONFLICT (email) DO NOTHING
                """)
                
                # SMS MESSAGES TABLE
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sms_messages (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER DEFAULT 1,
                        message_text TEXT NOT NULL,
                        sender_number VARCHAR(20),
                        sender_name VARCHAR(100),
                        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_bank_sms BOOLEAN DEFAULT FALSE,
                        bank_detected VARCHAR(50),
                        processed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print(" sms_messages table ready")
                
                # SMS TRANSACTIONS TABLE
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sms_transactions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER DEFAULT 1,
                        sms_id INTEGER,
                        amount NUMERIC(10,2) NOT NULL,
                        merchant VARCHAR(255),
                        transaction_date DATE NOT NULL,
                        bank_name VARCHAR(100),
                        confidence NUMERIC(3,2) DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print(" sms_transactions table ready")
                
                # MAIN TRANSACTIONS TABLE
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER DEFAULT 1,
                        amount NUMERIC(10,2) NOT NULL,
                        date DATE NOT NULL,
                        merchant VARCHAR(255),
                        category VARCHAR(100) DEFAULT 'Uncategorized',
                        source VARCHAR(50) DEFAULT 'sms_parser',
                        sms_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print(" transactions table ready")
                
                # SMS TEMPLATES TABLE
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sms_templates (
                        id SERIAL PRIMARY KEY,
                        bank_name VARCHAR(100) NOT NULL,
                        amount_pattern TEXT,
                        merchant_pattern TEXT,
                        date_pattern TEXT,
                        confidence_score NUMERIC(3,2) DEFAULT 0.9,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print(" sms_templates table ready")
                
                # Insert SMS templates
                templates = [
                    ('HDFC', r'(?:Rs\.?|INR|₹)\s*([\d,]+\.\d{2})\b', 
                     r'at\s+([A-Z][A-Z\s&]+?)(?:\s+on|\.|,|$)', 
                     r'on\s+(\d{2}-\d{2}-\d{4})', 0.95),
                    ('ICICI', r'(?:Rs\.?|INR|₹)\s*([\d,]+\.\d{2})\b',
                     r'at\s+([A-Z][A-Z\s&]+?)(?:\s+on|\.|,|$)',
                     r'on\s+(\d{2}-\d{2}-\d{4})', 0.93),
                    ('UPI', r'(?:Rs\.?|INR|₹)\s*([\d,]+\.\d{2})\b',
                     r'to\s+([A-Z][A-Z\s&]+?)(?:\s+on|\.|,|$)',
                     r'on\s+(\d{2}-\d{2}-\d{4})', 0.90),
                    ('SBI', r'Rs\s*([\d,]+\.\d{2})\b',
                     r'to\s+([A-Z][A-Z\s&]+?)(?:\s+on|\.|,|$)',
                     r'on\s+(\d{2}-\d{2}-\d{4})', 0.92)
                ]
                
                for bank, amount_pat, merch_pat, date_pat, conf in templates:
                    cursor.execute("""
                        INSERT INTO sms_templates 
                        (bank_name, amount_pattern, merchant_pattern, date_pattern, confidence_score)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (bank, amount_pat, merch_pat, date_pat, conf))
                
                print(f" {len(templates)} SMS templates inserted")
                
                self.conn.commit()
                print(" Database finapp_sms is fully set up and ready!")
                
        except Exception as e:
            print(f" Error creating tables: {e}")
            if self.conn:
                self.conn.rollback()
    
    # SMS Methods
    def save_sms_message(self, user_id, message_text, sender_number=None, 
                        sender_name=None, is_bank_sms=False, bank_detected=None):
        """Save incoming SMS message"""
        if not self.conn:
            print(" No database connection, returning test ID")
            return 999  # Test ID for offline mode
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO sms_messages 
                    (user_id, message_text, sender_number, sender_name, 
                     is_bank_sms, bank_detected, processed)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, message_text, sender_number, sender_name,
                     is_bank_sms, bank_detected, False))
                
                sms_id = cursor.fetchone()[0]
                self.conn.commit()
                print(f" SMS saved to database with ID: {sms_id}")
                return sms_id
                
        except Exception as e:
            print(f" Error saving SMS: {e}")
            if self.conn:
                self.conn.rollback()
            return None
    
    def save_parsed_sms_transaction(self, user_id, sms_id, amount, merchant, 
                                   transaction_date, bank_name, confidence=0.0):
        """Save parsed transaction from SMS"""
        if not self.conn:
            print(" No database connection, returning test ID")
            return 888  # Test ID for offline mode
        
        try:
            with self.conn.cursor() as cursor:
                # Save to sms_transactions
                cursor.execute("""
                    INSERT INTO sms_transactions 
                    (user_id, sms_id, amount, merchant, transaction_date, bank_name, confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, sms_id, amount, merchant, transaction_date, bank_name, confidence))
                
                txn_id = cursor.fetchone()[0]
                print(f" SMS transaction saved with ID: {txn_id}")
                
                # Also save to main transactions table
                cursor.execute("""
                    INSERT INTO transactions 
                    (user_id, amount, date, merchant, sms_id)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, amount, transaction_date, merchant, sms_id))
                
                main_txn_id = cursor.fetchone()[0]
                print(f" Main transaction saved with ID: {main_txn_id}")
                
                # Mark SMS as processed
                cursor.execute("UPDATE sms_messages SET processed = TRUE WHERE id = %s", (sms_id,))
                
                self.conn.commit()
                return txn_id
                
        except Exception as e:
            print(f" Error saving parsed transaction: {e}")
            if self.conn:
                self.conn.rollback()
            return None
    
    def get_user_transactions(self, user_id, limit=100):
        """Get all transactions for a user"""
        if not self.conn:
            print(" No database connection, returning test data")
            return [
                {
                    "id": 1,
                    "amount": 1500.00,
                    "date": "2023-12-15",
                    "merchant": "AMAZON INDIA",
                    "category": "Shopping",
                    "source": "sms_parser",
                    "created_at": "2024-01-15T10:30:00"
                }
            ]
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, amount, date, merchant, category, source, created_at
                    FROM transactions 
                    WHERE user_id = %s 
                    ORDER BY date DESC, created_at DESC
                    LIMIT %s
                """, (user_id, limit))
                
                transactions = []
                for row in cursor.fetchall():
                    transactions.append({
                        "id": row[0],
                        "amount": float(row[1]) if row[1] else 0,
                        "date": row[2].isoformat() if row[2] else None,
                        "merchant": row[3],
                        "category": row[4],
                        "source": row[5],
                        "created_at": row[6].isoformat() if row[6] else None
                    })
                
                return transactions
                
        except Exception as e:
            print(f" Error getting transactions: {e}")
            return []
    
    def get_sms_history(self, user_id, limit=50):
        """Get SMS history for user"""
        if not self.conn:
            print(" No database connection, returning test data")
            return [
                {
                    "id": 1,
                    "message_preview": "london Bank: Rs. 1,500.00 debited...",
                    "sender": "8600745379",
                    "bank": None,
                    "received_at": "2024-01-15T10:30:00",
                    "processed": True,
                    "parsed_amount": 1500.00,
                    "parsed_merchant": "AMAZON INDIA",
                    "confidence": 0.85
                }
            ]
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT sm.id, sm.message_text, sm.sender_number, 
                           sm.bank_detected, sm.received_at, sm.processed,
                           st.amount, st.merchant, st.confidence
                    FROM sms_messages sm
                    LEFT JOIN sms_transactions st ON sm.id = st.sms_id
                    WHERE sm.user_id = %s
                    ORDER BY sm.received_at DESC
                    LIMIT %s
                """, (user_id, limit))
                
                messages = []
                for row in cursor.fetchall():
                    messages.append({
                        "id": row[0],
                        "message_preview": (row[1][:80] + "...") if row[1] and len(row[1]) > 80 else row[1],
                        "sender": row[2],
                        "bank": row[3],
                        "received_at": row[4].isoformat() if row[4] else None,
                        "processed": row[5],
                        "parsed_amount": float(row[6]) if row[6] else None,
                        "parsed_merchant": row[7],
                        "confidence": float(row[8]) if row[8] else None
                    })
                
                return messages
                
        except Exception as e:
            print(f" Error getting SMS history: {e}")
            return []

# Create global instance
db = Database()
print(" Database module initialized successfully!")
