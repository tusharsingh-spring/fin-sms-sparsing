from database import db
print("\nDatabase Connection Test:")
print("Connection status:", "Connected" if db.conn else "Not connected")

if db.conn:
    try:
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sms_messages")
        count = cursor.fetchone()[0]
        print("Total SMS in database:", count)
        
        cursor.execute("SELECT COUNT(*) FROM transactions")
        count = cursor.fetchone()[0]
        print("Total transactions:", count)
        
        print(" Database is working correctly!")
    except Exception as e:
        print(" Database query failed:", e)
else:
    print(" Running in offline mode")
