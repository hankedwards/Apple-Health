from pathlib import Path

HEALTH_DATA = Path(
    "/home/hank/Downloads/Health/Healthexport/apple_health_export"
)

export_file = HEALTH_DATA / "export.xml"

print(f"Health-data folder: {HEALTH_DATA}")
print(f"Export file exists: {export_file.exists()}")

if export_file.exists():
    size_gb = export_file.stat().st_size / (1024 ** 3)
    print(f"Export file size: {size_gb:.2f} GB")
