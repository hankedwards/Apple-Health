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

    stage_map = {
        "HKCategoryValueSleepAnalysisAsleepCore": "Core",
        "HKCategoryValueSleepAnalysisAsleepDeep": "Deep",
        "HKCategoryValueSleepAnalysisAsleepREM": "REM",
        "HKCategoryValueSleepAnalysisAwake": "Awake",
        "HKCategoryValueSleepAnalysisInBed": "In Bed",
        "HKCategoryValueSleepAnalysisAsleep": "Asleep",
        "HKCategoryValueSleepAnalysisAsleepUnspecified": "Asleep Unspecified"
    }

    df["sleep_stage"] = df["sleep_stage"].replace(stage_map)
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
    # df["sleep_stage"] = df["sleep_stage"].replace(stage_map)
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
    # nightly = add_sleep_totals(nightly)

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

    import plotly.express as px

# Select the sleep-stage columns that actually exist
stage_columns = [
    col for col in ["Core", "Deep", "REM", "Awake"]
    if col in nightly.columns
]

# Convert from hours to minutes for easier reading
chart_data = nightly[
    ["sleep_date"] + stage_columns
].copy()

for stage in stage_columns:
    chart_data[stage] = chart_data[stage] * 60

# Convert wide data to long format for Plotly
chart_data = chart_data.melt(
    id_vars="sleep_date",
    value_vars=stage_columns,
    var_name="Sleep Stage",
    value_name="Minutes"
)

# Create stacked bar chart
fig = px.bar(
    chart_data,
    x="sleep_date",
    y="Minutes",
    color="Sleep Stage",
    title="Sleep Stages by Night",
    labels={
        "sleep_date": "Date",
        "Minutes": "Minutes"
    }
)

fig.update_layout(
    barmode="stack",
    xaxis_title="Date",
    yaxis_title="Minutes of Sleep",
    hovermode="x unified"
)

fig.show()

import plotly.express as px

# Make sure data is sorted by date
nightly = nightly.sort_values("sleep_date").copy()

# Calculate a 7-night moving average
nightly["7_day_avg"] = (
    nightly["total_sleep"]
    .rolling(window=7, min_periods=1)
    .mean()
)
print()
print("Sleep Hours by Stage and Date")
print("=" * 80)

# Select the columns we want to display
display_columns = [
    col for col in ["sleep_date", "Core", "Deep", "REM", "Awake", "total_sleep"]
    if col in nightly.columns
]

# Print with 2 decimal places
print(
    nightly[display_columns]
    .round(2)
    .to_string(index=False)
)
# Optional: only show the most recent 60 nights
chart_data = nightly.tail(60).copy()

fig = px.line(
    chart_data,
    x="sleep_date",
    y=["total_sleep", "7_day_avg"],
    title="Total Sleep per Night with 7-Day Moving Average",
    labels={
        "sleep_date": "Date",
        "value": "Hours of Sleep",
        "variable": "Measure"
    }
)

fig.update_traces(mode="lines+markers")

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Hours of Sleep",
    hovermode="x unified"
)

fig.for_each_trace(
    lambda trace: trace.update(
        name={
            "total_sleep": "Total Sleep",
            "7_day_avg": "7-Day Average"
        }.get(trace.name, trace.name)
    )
)
fig.show()