"""Central settings for WeatherVision Pro.

This file keeps paths, API URLs, chart colors, and weather-code labels in one
place. A beginner-friendly way to think about this file: the rest of the app
asks `config.py` where things live instead of repeating those details in every
module.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "WeatherVision Pro"
APP_ID = "WeatherVisionPro.Desktop"
APP_VERSION = "1.0.0"


def project_root() -> Path:
    """Return the folder that contains the application source files."""

    return Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    """Find bundled assets in both development and PyInstaller builds.

    PyInstaller extracts bundled files into a temporary folder named `_MEIPASS`.
    During normal development, assets are beside this Python file. This helper
    hides that difference so the UI can load icons the same way in both modes.
    """

    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", project_root()))
    else:
        base = project_root()
    return base.joinpath(*parts)


def writable_root() -> Path:
    """Return the folder where the app is allowed to write user data.

    In development we keep data inside the project so it is easy to inspect.
    In an installed EXE, Program Files is often read-only, so we write to the
    user's LocalAppData folder instead.
    """

    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(local_app_data) / APP_NAME
    return project_root()


BASE_DIR = project_root()
ASSETS_DIR = resource_path("assets")
ICON_DIR = ASSETS_DIR / "icons"
IMAGE_DIR = ASSETS_DIR / "images"
SPLASH_DIR = ASSETS_DIR / "splash"
THEME_DIR = ASSETS_DIR / "themes"

DATA_DIR = writable_root()
CACHE_DIR = DATA_DIR / "cache"
EXPORT_DIR = DATA_DIR / "exports"
DATABASE_DIR = DATA_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "weathervision.sqlite3"

APP_ICON_PATH = ICON_DIR / "weather_icon.ico"
APP_ICON_PNG_PATH = ICON_DIR / "weather_icon.png"

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

REQUEST_TIMEOUT_SECONDS = 15
FORECAST_CACHE_MINUTES = 15
AIR_QUALITY_CACHE_MINUTES = 30
HISTORICAL_CACHE_MINUTES = 12 * 60
GEOCODING_CACHE_MINUTES = 30 * 24 * 60

DEFAULT_CITY = "New York"
DEFAULT_AUTO_REFRESH_MINUTES = 15
HISTORICAL_DAYS = 45

LIGHT_THEME = "flatly"
DARK_THEME = "darkly"

FORECAST_CURRENT_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "is_day",
    "precipitation",
    "rain",
    "weather_code",
    "cloud_cover",
    "pressure_msl",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]

FORECAST_HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation",
    "rain",
    "weather_code",
    "pressure_msl",
    "surface_pressure",
    "wind_speed_10m",
    "wind_gusts_10m",
    "visibility",
    "uv_index",
    "is_day",
    "cloud_cover",
]

FORECAST_DAILY_VARIABLES = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "sunrise",
    "sunset",
    "daylight_duration",
    "sunshine_duration",
    "uv_index_max",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
]

HISTORICAL_HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "pressure_msl",
]

HISTORICAL_DAILY_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "wind_speed_10m_max",
]

AIR_QUALITY_CURRENT_VARIABLES = [
    "european_aqi",
    "us_aqi",
    "pm10",
    "pm2_5",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "ozone",
]

AIR_QUALITY_HOURLY_VARIABLES = [
    "european_aqi",
    "us_aqi",
    "pm10",
    "pm2_5",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "ozone",
]

WEATHER_CODE_LABELS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


def weather_label(code: int | float | None) -> str:
    """Convert an Open-Meteo WMO weather code into readable text."""

    if code is None:
        return "Unavailable"
    try:
        return WEATHER_CODE_LABELS.get(int(code), f"Weather code {int(code)}")
    except (TypeError, ValueError):
        return "Unavailable"


def icon_name_for_weather(code: int | float | None, is_day: bool = True) -> str:
    """Pick one local icon file name for a WMO weather code."""

    try:
        numeric_code = int(code)
    except (TypeError, ValueError):
        return "unknown.png"

    if numeric_code == 0:
        return "sun.png" if is_day else "moon.png"
    if numeric_code in {1, 2}:
        return "partly_cloudy.png" if is_day else "night_cloudy.png"
    if numeric_code == 3:
        return "cloud.png"
    if numeric_code in {45, 48}:
        return "fog.png"
    if numeric_code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
        return "rain.png"
    if numeric_code in {71, 73, 75, 77, 85, 86}:
        return "snow.png"
    if numeric_code in {95, 96, 99}:
        return "storm.png"
    return "unknown.png"


PALETTES = {
    "light": {
        "bg": "#f5f7fb",
        "sidebar": "#172033",
        "surface": "#ffffff",
        "card": "#ffffff",
        "card_alt": "#eef5ff",
        "text": "#18202f",
        "muted": "#6c788a",
        "accent": "#0ea5e9",
        "accent_2": "#22c55e",
        "warning": "#f59e0b",
        "danger": "#ef4444",
        "grid": "#d8e1ef",
        "chart_bg": "#ffffff",
    },
    "dark": {
        "bg": "#0d1117",
        "sidebar": "#080c12",
        "surface": "#111827",
        "card": "#161f2e",
        "card_alt": "#1f2a3d",
        "text": "#f8fafc",
        "muted": "#aeb8c7",
        "accent": "#38bdf8",
        "accent_2": "#34d399",
        "warning": "#fbbf24",
        "danger": "#fb7185",
        "grid": "#2d3748",
        "chart_bg": "#111827",
    },
}


def ensure_app_folders() -> None:
    """Create local folders that the app writes to."""

    for folder in (CACHE_DIR, EXPORT_DIR, DATABASE_DIR):
        folder.mkdir(parents=True, exist_ok=True)
