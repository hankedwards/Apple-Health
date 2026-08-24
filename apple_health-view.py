import sqlite3

conn = sqlite3.connect("apple_health.db")

cursor = conn.cursor()

cursor.execute("PRAGMA table_info(sleep_records)")

for row in cursor.fetchall():
    print(row)

conn.close()