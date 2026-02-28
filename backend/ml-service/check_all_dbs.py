import sqlite3
import os

databases = ['ihvn.db', 'iit_ml.db', 'iit_ml_service.db']

for db_name in databases:
    if not os.path.exists(db_name):
        print(f"\n{'='*60}")
        print(f"{db_name}: DOES NOT EXIST")
        print(f"{'='*60}")
        continue
    
    size = os.path.getsize(db_name)
    print(f"\n{'='*60}")
    print(f"{db_name}: {size} bytes")
    print(f"{'='*60}")
    
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        if tables:
            print(f"Tables ({len(tables)}):")
            for table in tables:
                print(f"  - {table[0]}")
                
            # Check for users table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
            if cursor.fetchone():
                print("\n  [HAS USERS TABLE]")
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                print(f"  Users count: {user_count}")
        else:
            print("  NO TABLES!")
        
        conn.close()
    except Exception as e:
        print(f"  ERROR: {e}")
