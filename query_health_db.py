import sqlite3

conn = sqlite3.connect("apple_health.db")
cursor = conn.cursor()

cursor.execute("""
SELECT
    start_date,
    duration,
    distance,
    distance_unit,
    stroke_count,
    active_calories,
    lap_length,
    lap_count
FROM swimming_workouts
ORDER BY start_date
LIMIT 10
""")

print("FIRST 10 SWIMS")
print("-" * 100)

for row in cursor.fetchall():
    print(row)

conn.close()