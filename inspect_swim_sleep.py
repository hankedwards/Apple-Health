import xml.etree.ElementTree as ET
from collections import Counter

FILE = "/home/hank/Downloads/Health/Healthexport/apple_health_export/export.xml"

swim_count = 0
sleep_count = 0

sleep_values = Counter()

print("Scanning Apple Health export...\n")

for event, elem in ET.iterparse(FILE, events=("end",)):

    # --------------------------
    # Swimming workouts
    # --------------------------
    if elem.tag == "Workout":
        workout_type = elem.attrib.get("workoutActivityType", "")

        if "Swimming" in workout_type:
            swim_count += 1

            # Print first 5 swimming workouts
            if swim_count <= 5:
                print("SWIMMING WORKOUT")
                print("Date:      ", elem.attrib.get("startDate"))
                print("Duration:  ", elem.attrib.get("duration"),
                      elem.attrib.get("durationUnit"))
                print("Distance:  ", elem.attrib.get("totalDistance"),
                      elem.attrib.get("totalDistanceUnit"))
                print("Calories:  ", elem.attrib.get("totalEnergyBurned"),
                      elem.attrib.get("totalEnergyBurnedUnit"))
                print()

    # --------------------------
    # Sleep records
    # --------------------------
    elif elem.tag == "Record":
        record_type = elem.attrib.get("type", "")

        if record_type == "HKCategoryTypeIdentifierSleepAnalysis":
            sleep_count += 1

            value = elem.attrib.get("value", "")
            sleep_values[value] += 1

            # Print first 5 sleep records
            if sleep_count <= 5:
                print("SLEEP RECORD")
                print("Stage: ", value)
                print("Start: ", elem.attrib.get("startDate"))
                print("End:   ", elem.attrib.get("endDate"))
                print()

    elem.clear()


print("\n----------------------------")
print("SUMMARY")
print("----------------------------")

print(f"Swimming workouts: {swim_count}")
print(f"Sleep records:      {sleep_count}")

print("\nSleep categories found:")

for stage, count in sleep_values.items():
    print(f"{stage}: {count}")