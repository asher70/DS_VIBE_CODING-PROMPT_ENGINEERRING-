"""Test charts generation with real API data."""
import sys
import os

# Use non-interactive backend for testing (no display needed)
import matplotlib
matplotlib.use("Agg")

sys.path.insert(0, ".")

from config import ensure_app_folders, EXPORT_DIR
ensure_app_folders()

from database import WeatherDatabase
from weather_api import OpenMeteoClient
from analytics import WeatherAnalytics
from charts import ChartFactory, build_plotly_dashboard
from pathlib import Path

print("Fetching real data for London...")
db = WeatherDatabase()
client = OpenMeteoClient(db)
bundle = client.fetch_by_city("London")
analytics = WeatherAnalytics(bundle)

print("Testing all 15 chart builders...")
factory = ChartFactory(analytics, dark_mode=False)
defs = factory.chart_definitions()
print(f"  Found {len(defs)} chart definitions")

errors = []
for chart_id, title, builder in defs:
    try:
        fig = builder()
        if fig is None:
            errors.append(f"{chart_id}: returned None")
        else:
            print(f"  [OK] {title}")
    except Exception as e:
        errors.append(f"{chart_id}: {e}")
        print(f"  [FAIL] {title}: {e}")

if errors:
    print(f"\n{len(errors)} chart(s) failed:")
    for e in errors:
        print(f"  - {e}")
else:
    print("\nAll 15 charts built successfully!")

print("\nTesting Plotly interactive dashboard...")
try:
    out = EXPORT_DIR / "test_plotly_dashboard.html"
    build_plotly_dashboard(analytics, out)
    print(f"  Plotly dashboard saved: {out}")
    size_kb = out.stat().st_size // 1024
    print(f"  File size: {size_kb} KB")
    print("  Plotly dashboard: OK")
except Exception as e:
    print(f"  Plotly dashboard ERROR: {e}")

print("\nALL CHART TESTS COMPLETE!")
