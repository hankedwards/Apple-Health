import sqlite3
import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "apple_health.db"


# ---------------------------------------------------------
# LOAD SLEEP DATA FROM DATABASE
# ---------------------------------------------------------

def load_sleep_data():
    conn = sqlite3.connect(DB_FILE)

    query = """
        SELECT
            id,
            sleep_stage,
            start_date,
            end_date,
            source_name
        FROM sleep_records
        ORDER BY start_date
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    # Convert dates to pandas datetime
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])

    # Calculate duration
    df["duration_hours"] = (
        (df["end_date"] - df["start_date"])
        .dt.total_seconds() / 3600
    )

    return df


# ---------------------------------------------------------
# CREATE NIGHTLY SUMMARY
# ---------------------------------------------------------

def create_nightly_summary(df):
    df = df.copy()

    # Subtract 12 hours so records after midnight
    # are assigned to the previous night's sleep.
    df["sleep_date"] = (
        df["start_date"] - pd.Timedelta(hours=12)
    ).dt.date

    summary = (
        df.pivot_table(
            index="sleep_date",
            columns="sleep_stage",
            values="duration_hours",
            aggfunc="sum",
            fill_value=0
        )
        .reset_index()
    )

    return summary


# ---------------------------------------------------------
# ADD TOTAL SLEEP
# ---------------------------------------------------------

def add_sleep_totals(summary):
    summary = summary.copy()

    sleep_stages = [
        "Core",
        "Deep",
        "REM",
        "Asleep",
        "Asleep Unspecified"
    ]

    summary["total_sleep"] = 0.0

    for stage in sleep_stages:
        if stage in summary.columns:
            summary["total_sleep"] += summary[stage]

    summary["total_sleep_minutes"] = (
        summary["total_sleep"] * 60
    )

    return summary


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

if __name__ == "__main__":

    print("Database:")
    print(DB_FILE)

    sleep = load_sleep_data()

    print()
    print("Number of sleep records:")
    print(len(sleep))

    print()
    print("Sleep stages found:")
    print(sleep["sleep_stage"].value_counts())

    print()
    print("Date range:")
    print("First:", sleep["start_date"].min())
    print("Last: ", sleep["start_date"].max())

    print()
    print("Sample records:")
    print(sleep.tail(20).to_string(index=False))

    nightly = create_nightly_summary(sleep)
    nightly = add_sleep_totals(nightly)

    print()
    print("Nightly Sleep Summary")
    print("-" * 100)

    print(
        nightly.tail(30).to_string(index=False)
    )

    nightly.to_csv(
        BASE_DIR / "sleep_nightly_summary.csv",
        index=False
    )

    print()
    print("Created sleep_nightly_summary.csv")