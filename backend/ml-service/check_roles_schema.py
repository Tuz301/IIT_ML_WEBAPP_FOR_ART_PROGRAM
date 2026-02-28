import sqlite3

conn = sqlite3.connect('iit_ml_service.db')
cursor = conn.cursor()

print("=" * 60)
print("ROLES table schema:")
print("=" * 60)
cursor.execute('PRAGMA table_info(roles)')
for row in cursor.fetchall():
    print(f"  {row}")

print("\n" + "=" * 60)
print("PERMISSIONS table schema:")
print("=" * 60)
cursor.execute('PRAGMA table_info(permissions)')
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
