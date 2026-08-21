import xml.etree.ElementTree as ET

XML_FILE = "/home/hank/Downloads/Health/Healthexport/apple_health_export/export.xml"

inside_swim = False

for event, elem in ET.iterparse(XML_FILE, events=("start", "end")):

    # Beginning of a Workout
    if event == "start" and elem.tag == "Workout":
        workout_type = elem.attrib.get("workoutActivityType", "")

        if "Swimming" in workout_type:
            inside_swim = True

    # End of the swimming Workout
    elif event == "end" and elem.tag == "Workout" and inside_swim:

        print("WORKOUT ATTRIBUTES")
        print("-" * 60)

        for key, value in elem.attrib.items():
            print(f"{key}: {value}")

        print("\nCHILD ELEMENTS")
        print("-" * 60)

        for child in elem:
            print(f"\nTag: {child.tag}")

            for key, value in child.attrib.items():
                print(f"    {key}: {value}")

        # We only need one swimming workout
        break

    # Clear elements we're finished with to conserve RAM
    elif event == "end" and not inside_swim:
        elem.clear()