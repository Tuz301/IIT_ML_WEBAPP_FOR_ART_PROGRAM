import sqlite3
import os

db_path = 'ihvn.db'
print(f"Database exists: {os.path.exists(db_path)}")
print(f"Database size: {os.path.getsize(db_path) if os.path.exists(db_path) else 0} bytes")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n" + "=" * 60)
print("ALL TABLES in database:")
print("=" * 60)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = cursor.fetchall()
if tables:
    for table in tables:
        print(f"  - {table[0]}")
else:
    print("  NO TABLES FOUND!")

conn.close()
