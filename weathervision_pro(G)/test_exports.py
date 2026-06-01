"""Test all export features."""
import sys
import matplotlib
matplotlib.use("Agg")
sys.path.insert(0, ".")

from config import ensure_app_folders
ensure_app_folders()

from database import WeatherDatabase
from weather_api import OpenMeteoClient
from analytics import WeatherAnalytics
from export import WeatherExporter

print("Fetching data (may use cache)...")
db = WeatherDatabase()
client = OpenMeteoClient(db)
bundle = client.fetch_by_city("London")
analytics = WeatherAnalytics(bundle)
exporter = WeatherExporter(db)

print("\nTesting CSV export...")
try:
    paths = exporter.export_csv_bundle(analytics)
    print(f"  Exported {len(paths)} CSV files")
    for p in paths:
        print(f"    {p.name}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\nTesting Excel export...")
try:
    path = exporter.export_excel(analytics)
    size_kb = path.stat().st_size // 1024
    print(f"  Excel saved: {path.name} ({size_kb} KB)")
except Exception as e:
    print(f"  ERROR: {e}")

print("\nTesting PDF report export...")
try:
    path = exporter.export_pdf_report(analytics, dark_mode=False)
    size_kb = path.stat().st_size // 1024
    print(f"  PDF saved: {path.name} ({size_kb} KB)")
except Exception as e:
    print(f"  ERROR: {e}")

print("\nTesting PNG chart snapshots export...")
try:
    paths = exporter.export_chart_snapshots(analytics, dark_mode=False)
    print(f"  Exported {len(paths)} PNG files")
except Exception as e:
    print(f"  ERROR: {e}")

print("\nALL EXPORT TESTS COMPLETE!")
