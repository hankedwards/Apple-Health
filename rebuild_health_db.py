import os
import sqlite3
import xml.etree.ElementTree as ET

XML_FILE = "/home/hank/Downloads/Health/Healthexport/apple_health_export/export.xml"
DB_FILE = "apple_health.db"


# ---------------------------------------------------------
# Start with a clean database
# ---------------------------------------------------------
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print("Old database removed.")


conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()


# ---------------------------------------------------------
# Create swimming table
# ---------------------------------------------------------
cursor.execute("""
CREATE TABLE swimming_workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_date TEXT,
    end_date TEXT,
    duration REAL,
    duration_unit TEXT,
    distance REAL,
    distance_unit TEXT,
    stroke_count REAL,
    active_calories REAL,
    basal_calories REAL,
    lap_length TEXT,
    lap_count INTEGER,
    stroke_style TEXT,
    swimming_location_type TEXT,
    source_name TEXT
)
""")


# ---------------------------------------------------------
# Create sleep table
# ---------------------------------------------------------
cursor.execute("""
CREATE TABLE sleep_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sleep_stage TEXT,
    start_date TEXT,
    end_date TEXT,
    source_name TEXT
)
""")

conn.commit()


# ---------------------------------------------------------
# Scan XML
# ---------------------------------------------------------
swim_count = 0
sleep_count = 0

inside_swimming_workout = False

print("Reading Apple Health export...")

for event, elem in ET.iterparse(
        XML_FILE,
        events=("start", "end")
):

    # -----------------------------------------------------
    # Detect start of a swimming workout
    # -----------------------------------------------------
    if event == "start" and elem.tag == "Workout":

        workout_type = elem.attrib.get(
            "workoutActivityType", ""
        )

        inside_swimming_workout = (
            workout_type == "HKWorkoutActivityTypeSwimming"
        )

    # -----------------------------------------------------
    # Process completed swimming workout
    # -----------------------------------------------------
    elif (
        event == "end"
        and elem.tag == "Workout"
        and inside_swimming_workout
    ):

        distance = None
        distance_unit = None
        stroke_count = None
        active_calories = None
        basal_calories = None

        lap_length = None
        stroke_style = None
        swimming_location_type = None

        lap_count = 0

        # Examine everything inside the workout
        for child in elem:

            # ---------------------------------------------
            # Workout statistics
            # ---------------------------------------------
            if child.tag == "WorkoutStatistics":

                stat_type = child.attrib.get("type")
                value = child.attrib.get("sum")
                unit = child.attrib.get("unit")

                if stat_type == \
                        "HKQuantityTypeIdentifierDistanceSwimming":

                    distance = value
                    distance_unit = unit

                elif stat_type == \
                        "HKQuantityTypeIdentifierSwimmingStrokeCount":

                    stroke_count = value

                elif stat_type == \
                        "HKQuantityTypeIdentifierActiveEnergyBurned":

                    active_calories = value

                elif stat_type == \
                        "HKQuantityTypeIdentifierBasalEnergyBurned":

                    basal_calories = value

            # ---------------------------------------------
            # Pool / swimming metadata
            # ---------------------------------------------
            elif child.tag == "MetadataEntry":

                key = child.attrib.get("key")
                value = child.attrib.get("value")

                if key == "HKLapLength":
                    lap_length = value

                elif key == "HKSwimmingStrokeStyle":
                    stroke_style = value

                elif key == "HKSwimmingLocationType":
                    swimming_location_type = value

            # ---------------------------------------------
            # Count pool laps/lengths
            # ---------------------------------------------
            elif child.tag == "WorkoutEvent":

                if child.attrib.get("type") == \
                        "HKWorkoutEventTypeLap":

                    lap_count += 1

        # ---------------------------------------------
        # Insert workout into SQLite
        # ---------------------------------------------
        cursor.execute("""
            INSERT INTO swimming_workouts (
                start_date,
                end_date,
                duration,
                duration_unit,
                distance,
                distance_unit,
                stroke_count,
                active_calories,
                basal_calories,
                lap_length,
                lap_count,
                stroke_style,
                swimming_location_type,
                source_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            elem.attrib.get("startDate"),
            elem.attrib.get("endDate"),
            elem.attrib.get("duration"),
            elem.attrib.get("durationUnit"),
            distance,
            distance_unit,
            stroke_count,
            active_calories,
            basal_calories,
            lap_length,
            lap_count,
            stroke_style,
            swimming_location_type,
            elem.attrib.get("sourceName")
        ))

        swim_count += 1

        # Finished with this workout
        elem.clear()
        inside_swimming_workout = False

    # -----------------------------------------------------
    # Process sleep record
    # -----------------------------------------------------
    elif event == "end" and elem.tag == "Record":

        record_type = elem.attrib.get("type", "")

        if record_type == \
                "HKCategoryTypeIdentifierSleepAnalysis":

            cursor.execute("""
                INSERT INTO sleep_records (
                    sleep_stage,
                    start_date,
                    end_date,
                    source_name
                )
                VALUES (?, ?, ?, ?)
            """, (
                elem.attrib.get("value"),
                elem.attrib.get("startDate"),
                elem.attrib.get("endDate"),
                elem.attrib.get("sourceName")
            ))

            sleep_count += 1

        elem.clear()

    # -----------------------------------------------------
    # Clear unrelated XML elements to conserve Nano memory
    # Do NOT clear children of a swimming workout yet.
    # -----------------------------------------------------
    elif event == "end" and not inside_swimming_workout:
        elem.clear()

    # Commit periodically
    if (swim_count + sleep_count) > 0:
        if (swim_count + sleep_count) % 1000 == 0:
            conn.commit()


conn.commit()
conn.close()


print()
print("----------------------------------------")
print("IMPORT COMPLETE")
print("----------------------------------------")
print(f"Swimming workouts: {swim_count}")
print(f"Sleep records:      {sleep_count}")
print(f"Database:           {DB_FILE}")