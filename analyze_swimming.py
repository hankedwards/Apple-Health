import sqlite3
import pandas as pd

DB_FILE = "apple_health.db"

conn = sqlite3.connect(DB_FILE)

df = pd.read_sql_query("""
    SELECT *
    FROM swimming_workouts
    ORDER BY start_date
""", conn)

conn.close()

# Convert dates
df["start_date"] = pd.to_datetime(df["start_date"], utc=True, errors="coerce")
df["end_date"] = pd.to_datetime(df["end_date"], utc=True, errors="coerce")

# Make sure numeric columns are numeric
numeric_columns = [
    "duration",
    "distance",
    "stroke_count",
    "active_calories",
    "basal_calories",
    "lap_count"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Calculated fields
df["yards_per_minute"] = df["distance"] / df["duration"]

df["strokes_per_100_yards"] = (
    df["stroke_count"] / df["distance"] * 100
)

df["year"] = df["start_date"].dt.year
df["month"] = df["start_date"].dt.month

print("\nSWIMMING DATA")
print("-" * 100)

print(
    df[
        [
            "start_date",
            "duration",
            "distance",
            "stroke_count",
            "active_calories",
            "lap_count",
            "yards_per_minute",
            "strokes_per_100_yards"
        ]
    ].head(10)
)

print("\nSUMMARY")
print("-" * 100)

print(f"Number of swims: {len(df)}")
print(f"Total yards: {df['distance'].sum():,.0f}")
print(f"Average distance: {df['distance'].mean():,.0f} yards")
print(f"Average duration: {df['duration'].mean():.1f} minutes")
print(f"Average yards/minute: {df['yards_per_minute'].mean():.1f}")
print(f"Average strokes/100 yards: {df['strokes_per_100_yards'].mean():.1f}")

yearly = df.groupby("year").agg(
    swims=("id", "count"),
    total_yards=("distance", "sum"),
    avg_distance=("distance", "mean"),
    avg_duration=("duration", "mean"),
    avg_yards_per_minute=("yards_per_minute", "mean")
)

print("\nSWIMMING BY YEAR")
print("-" * 100)
print(yearly.round(1))

import plotly.express as px

fig = px.scatter(
    df,
    x="start_date",
    y="distance",
    title="Swimming Distance Over Time",
    labels={
        "start_date": "Date",
        "distance": "Distance (yards)"
    },
    hover_data=[
        "duration",
        "stroke_count",
        "active_calories",
        "yards_per_minute"
    ]
)

fig.show()