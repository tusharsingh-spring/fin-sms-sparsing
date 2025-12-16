import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

print("Testing PostgreSQL Connection...")
print(f"DB_HOST: {os.getenv('DB_HOST', 'localhost')}")
print(f"DB_NAME: {os.getenv('DB_NAME', 'finapp')}")
print(f"DB_USER: {os.getenv('DB_USER', 'postgres')}")
print(f"DB_PORT: {os.getenv('DB_PORT', '5432')}")

try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'finapp'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres123'),
        port=os.getenv('DB_PORT', '5432')
    )
    print(" PostgreSQL Connected Successfully!")
    
    # Test query
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"PostgreSQL Version: {version[0]}")
    
    # List databases
    cursor.execute("SELECT datname FROM pg_database;")
    databases = cursor.fetchall()
    print("\\nAvailable Databases:")
    for db in databases:
        print(f"  - {db[0]}")
    
    conn.close()
    
except Exception as e:
    print(f" Connection Failed: {e}")
    print("\\nTroubleshooting:")
    print("1. Is PostgreSQL installed and running?")
    print("2. Did you create the 'finapp' database?")
    print("3. Check credentials in .env file")
