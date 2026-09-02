import sqlite3
import json
import urllib.request
from pathlib import Path

import pandas as pd


# =========================================================
# CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "apple_health.db"

OLLAMA_URL = "http://localhost:11434/api/generate"

# Change this if your Ollama model has a different name.
# Run: ollama list
# to see your installed models.
OLLAMA_MODEL = "qwen2.5:7b"


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    return sqlite3.connect(DB_FILE)


# =========================================================
# SLEEP DATA
# =========================================================

def load_sleep_data():
    """
    Load sleep records from apple_health.db.
    """

    conn = get_connection()

    query = """
        SELECT
            sleep_stage,
            start_date,
            end_date,
            source_name
        FROM sleep_records
        ORDER BY start_date
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    if df.empty:
        return df

    df["start_date"] = pd.to_datetime(
        df["start_date"],
        errors="coerce"
    )

    df["end_date"] = pd.to_datetime(
        df["end_date"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["start_date", "end_date"]
    )

    df["duration_hours"] = (
        (df["end_date"] - df["start_date"])
        .dt.total_seconds()
        / 3600
    )

    # Assign after-midnight sleep to the previous night
    df["sleep_date"] = (
        df["start_date"] - pd.Timedelta(hours=12)
    ).dt.date

    return df


def create_nightly_sleep_summary(sleep):
    """
    Convert individual sleep-stage records into
    one record per night.
    """

    if sleep.empty:
        return pd.DataFrame()

    summary = (
        sleep.pivot_table(
            index="sleep_date",
            columns="sleep_stage",
            values="duration_hours",
            aggfunc="sum",
            fill_value=0
        )
        .reset_index()
    )

    # These are the stages that count as actual sleep
    actual_sleep_stages = [
        "Core",
        "Deep",
        "REM",
        "Asleep",
        "Asleep Unspecified"
    ]

    summary["total_sleep"] = 0.0

    for stage in actual_sleep_stages:
        if stage in summary.columns:
            summary["total_sleep"] += summary[stage]

    summary["sleep_date"] = pd.to_datetime(
        summary["sleep_date"]
    )

    summary = summary.sort_values("sleep_date")

    summary["7_day_average"] = (
        summary["total_sleep"]
        .rolling(7, min_periods=1)
        .mean()
    )

    return summary


def summarize_sleep(nightly, days=30):
    """
    Produce compact statistics suitable for an LLM prompt.
    """

    if nightly.empty:
        return "No sleep data available."

    cutoff = nightly["sleep_date"].max() - pd.Timedelta(
        days=days - 1
    )

    recent = nightly[
        nightly["sleep_date"] >= cutoff
    ].copy()

    if recent.empty:
        return "No recent sleep data available."

    result = []

    result.append(
        f"Sleep analysis for the most recent {len(recent)} nights:"
    )

    result.append(
        f"Average sleep: "
        f"{recent['total_sleep'].mean():.2f} hours"
    )

    result.append(
        f"Median sleep: "
        f"{recent['total_sleep'].median():.2f} hours"
    )

    result.append(
        f"Minimum sleep: "
        f"{recent['total_sleep'].min():.2f} hours"
    )

    result.append(
        f"Maximum sleep: "
        f"{recent['total_sleep'].max():.2f} hours"
    )

    result.append(
        f"Current 7-night moving average: "
        f"{recent['7_day_average'].iloc[-1]:.2f} hours"
    )

    for stage in ["Core", "Deep", "REM", "Awake"]:
        if stage in recent.columns:
            average_minutes = recent[stage].mean() * 60

            result.append(
                f"Average {stage}: "
                f"{average_minutes:.0f} minutes"
            )

    return "\n".join(result)


# =========================================================
# SWIMMING DATA
# =========================================================

def get_swimming_columns():
    """
    Read the swimming_workouts table structure.

    This allows the program to work even if we have
    slightly different column names.
    """

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        "PRAGMA table_info(swimming_workouts)"
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    conn.close()

    return columns


def load_swimming_data():
    """
    Load all swimming workouts.

    We load the full table because the exact column
    structure may vary.
    """

    conn = get_connection()

    swim = pd.read_sql_query(
        """
        SELECT *
        FROM swimming_workouts
        """,
        conn
    )

    conn.close()

    return swim


def find_column(columns, possibilities):
    """
    Find the first matching column name.
    """

    lower_lookup = {
        column.lower(): column
        for column in columns
    }

    for name in possibilities:
        if name.lower() in lower_lookup:
            return lower_lookup[name.lower()]

    return None


def summarize_swimming(swim, days=30):
    """
    Produce a compact swimming summary.

    The routine attempts to identify common field names
    automatically.
    """

    if swim.empty:
        return "No swimming data available."

    columns = list(swim.columns)

    date_column = find_column(
        columns,
        [
            "start_date",
            "startdate",
            "date",
            "workout_date",
            "creation_date"
        ]
    )

    duration_column = find_column(
        columns,
        [
            "duration",
            "duration_minutes",
            "duration_min",
            "workout_duration"
        ]
    )

    distance_column = find_column(
        columns,
        [
            "distance",
            "distance_meters",
            "total_distance",
            "distance_yards"
        ]
    )

    recent = swim.copy()

    result = []

    if date_column:
        recent[date_column] = pd.to_datetime(
            recent[date_column],
            errors="coerce"
        )

        recent = recent.dropna(
            subset=[date_column]
        )

        if not recent.empty:
            latest_date = recent[date_column].max()

            cutoff = latest_date - pd.Timedelta(
                days=days - 1
            )

            recent = recent[
                recent[date_column] >= cutoff
            ]

    result.append(
        f"Swimming analysis for the recent "
        f"{days}-day period:"
    )

    result.append(
        f"Number of swims: {len(recent)}"
    )

    if duration_column and not recent.empty:

        duration = pd.to_numeric(
            recent[duration_column],
            errors="coerce"
        )

        duration = duration.dropna()

        if not duration.empty:

            result.append(
                f"Average swim duration: "
                f"{duration.mean():.1f} minutes"
            )

            result.append(
                f"Total swim duration: "
                f"{duration.sum():.1f} minutes"
            )

    if distance_column and not recent.empty:

        distance = pd.to_numeric(
            recent[distance_column],
            errors="coerce"
        )

        distance = distance.dropna()

        if not distance.empty:

            result.append(
                f"Average recorded swim distance: "
                f"{distance.mean():.1f}"
            )

    result.append(
        "Swimming database columns: "
        + ", ".join(columns)
    )

    return "\n".join(result)


# =========================================================
# RECENT NIGHTLY DATA
# =========================================================

def recent_sleep_table(nightly, nights=14):
    """
    Give the LLM some individual nightly observations,
    not just averages.
    """

    if nightly.empty:
        return "No nightly sleep records."

    recent = nightly.tail(nights).copy()

    lines = []

    for _, row in recent.iterrows():

        line = (
            f"{row['sleep_date'].date()}: "
            f"{row['total_sleep']:.2f} hours"
        )

        stage_parts = []

        for stage in ["Core", "Deep", "REM", "Awake"]:

            if stage in recent.columns:

                minutes = row[stage] * 60

                stage_parts.append(
                    f"{stage} {minutes:.0f} min"
                )

        if stage_parts:
            line += " (" + ", ".join(stage_parts) + ")"

        lines.append(line)

    return "\n".join(lines)


# =========================================================
# OLLAMA
# =========================================================

def ask_ollama(prompt):
    """
    Send a prompt to the local Ollama server.
    """

    data = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    encoded_data = json.dumps(data).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        OLLAMA_URL,
        data=encoded_data,
        headers={
            "Content-Type": "application/json"
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=300
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

            return result.get(
                "response",
                "No response received."
            )

    except Exception as error:

        return (
            "\nUnable to communicate with Ollama.\n\n"
            f"Error: {error}\n\n"
            "Make sure Ollama is running and that "
            f"the model '{OLLAMA_MODEL}' is installed."
        )


# =========================================================
# BUILD THE LLM CONTEXT
# =========================================================

def build_health_context():
    """
    Query SQLite and construct a concise health-data
    context for the LLM.
    """

    sleep = load_sleep_data()

    nightly = create_nightly_sleep_summary(
        sleep
    )

    swim = load_swimming_data()

    sleep_summary = summarize_sleep(
        nightly,
        days=90
    )

    swim_summary = summarize_swimming(
        swim,
        days=90
    )

    recent_nights = recent_sleep_table(
        nightly,
        nights=21
    )

    context = f"""
APPLE HEALTH DATA
=================

SLEEP SUMMARY
-------------
{sleep_summary}


RECENT NIGHTLY SLEEP
--------------------
{recent_nights}


SWIMMING SUMMARY
----------------
{swim_summary}
"""

    return context


# =========================================================
# ASK A HEALTH QUESTION
# =========================================================

def ask_health_question(question):
    """
    Combine calculated Apple Health statistics with
    the user's question and send them to the LLM.
    """

    context = build_health_context()

    prompt = f"""
You are an assistant helping me explore my personal
Apple Health data.

Python and pandas have already calculated the statistics
below. Treat those calculated numbers as the source of
truth. Do not invent measurements that are not present.

I am interested in understanding patterns and trends,
particularly relationships between sleep and swimming.

Do not diagnose medical conditions. Clearly distinguish
between patterns shown by the data and possible
explanations that would require more evidence.

Here is my Apple Health data:

{context}

MY QUESTION
-----------
{question}

Please give me a clear, conversational analysis.
When useful:

- identify important patterns
- compare recent values with averages
- point out unusual observations
- explain possible relationships
- suggest additional analyses we could perform with
  the database

Keep the explanation understandable rather than highly
technical.
"""

    return ask_ollama(prompt)


# =========================================================
# INTERACTIVE PROGRAM
# =========================================================

def main():

    print()
    print("=" * 65)
    print("APPLE HEALTH AI ASSISTANT")
    print("=" * 65)

    print()
    print("Database:")
    print(DB_FILE)

    print()
    print("Ollama model:")
    print(OLLAMA_MODEL)

    print()
    print("Swimming table columns:")
    print(get_swimming_columns())

    print()
    print(
        "Ask questions about your sleep and swimming."
    )

    print(
        "Type 'summary' to see the data sent to the LLM."
    )

    print(
        "Type 'quit' to exit."
    )

    while True:

        print()

        question = input(
            "Health question: "
        ).strip()

        if not question:
            continue

        if question.lower() in [
            "quit",
            "exit",
            "q"
        ]:
            break

        if question.lower() == "summary":

            print()
            print(build_health_context())

            continue

        print()
        print("Analyzing...")
        print()

        answer = ask_health_question(
            question
        )

        print(answer)


if __name__ == "__main__":
    main()