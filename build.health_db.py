import sqlite3
import xml.etree.ElementTree as ET

XML_FILE = "/home/hank/Downloads/Health/Healthexport/apple_health_export/export.xml"
DB_FILE = "apple_health.db"


def create_database(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS swimming_workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_type TEXT,
            start_date TEXT,
            end_date TEXT,
            duration REAL,
            duration_unit TEXT,
            total_distance REAL,
            distance_unit TEXT,
            total_energy_burned REAL,
            energy_unit TEXT,
            source_name TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sleep_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sleep_stage TEXT,
            start_date TEXT,
            end_date TEXT,
            source_name TEXT
        )
    """)

    conn.commit()


def import_health_data():
    conn = sqlite3.connect(DB_FILE)
    create_database(conn)

    cursor = conn.cursor()

    swim_count = 0
    sleep_count = 0

    print("Importing Apple Health data...")

    for event, elem in ET.iterparse(XML_FILE, events=("end",)):

        # Swimming workouts
        if elem.tag == "Workout":
            workout_type = elem.attrib.get("workoutActivityType", "")

            if "Swimming" in workout_type:
                cursor.execute("""
                    INSERT INTO swimming_workouts (
                        workout_type,
                        start_date,
                        end_date,
                        duration,
                        duration_unit,
                        total_distance,
                        distance_unit,
                        total_energy_burned,
                        energy_unit,
                        source_name
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    workout_type,
                    elem.attrib.get("startDate"),
                    elem.attrib.get("endDate"),
                    elem.attrib.get("duration"),
                    elem.attrib.get("durationUnit"),
                    elem.attrib.get("totalDistance"),
                    elem.attrib.get("totalDistanceUnit"),
                    elem.attrib.get("totalEnergyBurned"),
                    elem.attrib.get("totalEnergyBurnedUnit"),
                    elem.attrib.get("sourceName")
                ))

                swim_count += 1

        # Sleep records
        elif elem.tag == "Record":
            record_type = elem.attrib.get("type", "")

            if record_type == "HKCategoryTypeIdentifierSleepAnalysis":
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

        # Commit periodically
        if (swim_count + sleep_count) % 1000 == 0:
            conn.commit()

    conn.commit()
    conn.close()

    print()
    print("Import complete.")
    print(f"Swimming workouts imported: {swim_count}")
    print(f"Sleep records imported:      {sleep_count}")
    print(f"Database created:            {DB_FILE}")


if __name__ == "__main__":
    import_health_data()