"""Quick smoke-test: check imports, API calls, and analytics."""
import sys
import traceback

sys.path.insert(0, ".")

from config import ensure_app_folders
ensure_app_folders()

from database import WeatherDatabase
from weather_api import OpenMeteoClient
from analytics import WeatherAnalytics

db = WeatherDatabase()
client = OpenMeteoClient(db)

print("Testing geocoding for London...")
try:
    loc = client.geocode_city("London")
    print(f"  Location: {loc.display_name}, lat={loc.latitude}, lon={loc.longitude}")
except Exception as e:
    print(f"  Geocoding ERROR: {e}")
    sys.exit(1)

print("Testing full bundle fetch (forecast + historical + air quality)...")
try:
    bundle = client.fetch_by_city("London")
    print(f"  Forecast keys  : {list(bundle.forecast.keys())[:6]}")
    print(f"  Historical keys: {list(bundle.historical.keys())[:6]}")
    print(f"  Air quality keys: {list(bundle.air_quality.keys())[:6]}")
    current = bundle.forecast.get("current", {})
    print(f"  Current temp   : {current.get('temperature_2m')} C")
    print(f"  Humidity       : {current.get('relative_humidity_2m')} %")
    print(f"  Wind speed     : {current.get('wind_speed_10m')} km/h")
    print(f"  Weather code   : {current.get('weather_code')}")
except Exception as e:
    traceback.print_exc()
    sys.exit(1)

print("Testing analytics layer...")
try:
    analytics = WeatherAnalytics(bundle)
    conditions = analytics.current_conditions()
    print(f"  Condition label: {conditions.get('weather_label')}")
    metrics = analytics.summary_metrics()
    for k, v in metrics.items():
        print(f"  {k:20s}: {v}")
    trend = analytics.temperature_trend_label()
    print(f"  Trend: {trend}")
    rows = analytics.weekly_forecast_rows()
    print(f"  Weekly rows: {len(rows)} days")
    hourly = analytics.hourly_rows(6)
    print(f"  Hourly rows: {len(hourly)} slots (first 6)")
except Exception as e:
    traceback.print_exc()
    sys.exit(1)

print("\nALL TESTS PASSED - WeatherVision Pro API integration is working correctly!")
