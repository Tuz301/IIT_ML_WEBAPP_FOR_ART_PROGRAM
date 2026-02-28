import sqlite3

conn = sqlite3.connect('iit_ml_service.db')
cursor = conn.cursor()

print("=" * 60)
print("USER_ROLES table schema (from iit_ml_service.db):")
print("=" * 60)
cursor.execute('PRAGMA table_info(user_roles)')
for row in cursor.fetchall():
    print(f"  {row}")

print("\n" + "=" * 60)
print("ROLE_PERMISSIONS table schema (from iit_ml_service.db):")
print("=" * 60)
cursor.execute('PRAGMA table_info(role_permissions)')
for row in cursor.fetchall():
    print(f"  {row}")

print("\n" + "=" * 60)
print("USERS table schema (from iit_ml_service.db):")
print("=" * 60)
cursor.execute('PRAGMA table_info(users)')
for row in cursor.fetchall():
    print(f"  {row}")

print("\n" + "=" * 60)
print("Foreign Key info for USER_ROLES:")
print("=" * 60)
cursor.execute('PRAGMA foreign_key_list(user_roles)')
for row in cursor.fetchall():
    print(f"  {row}")

print("\n" + "=" * 60)
print("Foreign Key info for ROLE_PERMISSIONS:")
print("=" * 60)
cursor.execute('PRAGMA foreign_key_list(role_permissions)')
for row in cursor.fetchall():
    print(f"  {row}")

print("\n" + "=" * 60)
print("Sample data from USERS:")
print("=" * 60)
cursor.execute('SELECT id, username, email, is_active, is_superuser FROM users')
for row in cursor.fetchall():
    print(f"  {row}")

print("\n" + "=" * 60)
print("Sample data from USER_ROLES:")
print("=" * 60)
cursor.execute('SELECT * FROM user_roles')
for row in cursor.fetchall():
    print(f"  {row}")

print("\n" + "=" * 60)
print("Sample data from ROLES:")
print("=" * 60)
cursor.execute('SELECT * FROM roles')
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
