import sqlite3

conn = sqlite3.connect('iit_ml_service.db')
c = conn.cursor()

print('user_roles schema:')
c.execute('PRAGMA table_info(user_roles)')
for row in c.fetchall():
    print(row)

print('\nrole_permissions schema:')
c.execute('PRAGMA table_info(role_permissions)')
for row in c.fetchall():
    print(row)

conn.close()
