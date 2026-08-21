import xml.etree.ElementTree as ET

FILE = "/home/hank/Downloads/Health/Healthexport/apple_health_export/export.xml"

record_types = set()

for event, elem in ET.iterparse(FILE, events=("end",)):
    if elem.tag == "Record":
        record_type = elem.attrib.get("type")
        if record_type:
            record_types.add(record_type)
        elem.clear()

print(f"Found {len(record_types)} record types:\n")

for record_type in sorted(record_types):
    print(record_type)