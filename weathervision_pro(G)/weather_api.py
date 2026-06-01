"""Open-Meteo API client.

This module is the only place that talks to weather services. Every weather
number shown in the app comes from Open-Meteo JSON. The rest of the program
receives already-downloaded dictionaries and never invents values.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import requests

from config import (
    AIR_QUALITY_CACHE_MINUTES,
    AIR_QUALITY_CURRENT_VARIABLES,
    AIR_QUALITY_HOURLY_VARIABLES,
    FORECAST_CACHE_MINUTES,
    FORECAST_CURRENT_VARIABLES,
    FORECAST_DAILY_VARIABLES,
    FORECAST_HOURLY_VARIABLES,
    GEOCODING_CACHE_MINUTES,
    HISTORICAL_CACHE_MINUTES,
    HISTORICAL_DAILY_VARIABLES,
    HISTORICAL_DAYS,
    HISTORICAL_HOURLY_VARIABLES,
    OPEN_METEO_AIR_QUALITY_URL,
    OPEN_METEO_ARCHIVE_URL,
    OPEN_METEO_FORECAST_URL,
    OPEN_METEO_GEOCODING_URL,
    REQUEST_TIMEOUT_SECONDS,
)
from database import WeatherDatabase


class WeatherApiError(RuntimeError):
    """Friendly exception type for expected API and connectivity failures."""


@dataclass(frozen=True)
class LocationResult:
    """A resolved place or coordinate pair used by Open-Meteo."""

    name: str
    country: str | None
    latitude: float
    longitude: float
    timezone: str | None = None
    admin1: str | None = None

    @property
    def display_name(self) -> str:
        pieces = [self.name]
        if self.admin1:
            pieces.append(self.admin1)
        if self.country:
            pieces.append(self.country)
        return ", ".join(piece for piece in pieces if piece)


@dataclass
class WeatherBundle:
    """All real weather data needed by the dashboard."""

    location: LocationResult
    forecast: dict[str, Any]
    historical: dict[str, Any]
    air_quality: dict[str, Any]


class OpenMeteoClient:
    """Small, cached client for Open-Meteo forecast, archive, and AQI APIs."""

    def __init__(self, database: WeatherDatabase | None = None) -> None:
        self.database = database or WeatherDatabase()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "WeatherVisionPro/1.0 "
                    "(local desktop app; Open-Meteo public API)"
                )
            }
        )

    def geocode_city(self, city: str) -> LocationResult:
        """Convert a city name into latitude and longitude."""

        cleaned_city = city.strip()
        if not cleaned_city:
            raise WeatherApiError("Please enter a city name.")

        params = {
            "name": cleaned_city,
            "count": 1,
            "language": "en",
            "format": "json",
        }
        data = self._get_json(
            "geocoding",
            OPEN_METEO_GEOCODING_URL,
            params,
            GEOCODING_CACHE_MINUTES,
        )
        results = data.get("results") or []
        if not results:
            raise WeatherApiError(f"No Open-Meteo location found for '{cleaned_city}'.")

        first = results[0]
        return LocationResult(
            name=first.get("name", cleaned_city),
            country=first.get("country"),
            latitude=float(first["latitude"]),
            longitude=float(first["longitude"]),
            timezone=first.get("timezone"),
            admin1=first.get("admin1"),
        )

    def fetch_by_city(self, city: str) -> WeatherBundle:
        """Resolve a city and download all required weather datasets."""

        location = self.geocode_city(city)
        bundle = self.fetch_by_location(location)
        self.database.save_search(
            location.name,
            location.country,
            location.latitude,
            location.longitude,
            location.timezone,
        )
        return bundle

    def fetch_by_location(self, location: LocationResult) -> WeatherBundle:
        """Download forecast, historical, and air quality data in parallel."""

        with ThreadPoolExecutor(max_workers=3) as executor:
            forecast_future = executor.submit(self.fetch_forecast, location)
            historical_future = executor.submit(self.fetch_historical, location)
            air_quality_future = executor.submit(self.fetch_air_quality, location)

            forecast = forecast_future.result()
            historical = historical_future.result()
            air_quality = air_quality_future.result()

        return WeatherBundle(
            location=location,
            forecast=forecast,
            historical=historical,
            air_quality=air_quality,
        )

    def fetch_forecast(self, location: LocationResult) -> dict[str, Any]:
        """Fetch current, hourly, and 7-day forecast data."""

        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": ",".join(FORECAST_CURRENT_VARIABLES),
            "hourly": ",".join(FORECAST_HOURLY_VARIABLES),
            "daily": ",".join(FORECAST_DAILY_VARIABLES),
            "timezone": "auto",
            "forecast_days": 7,
            "past_days": 1,
        }
        return self._get_json(
            "forecast",
            OPEN_METEO_FORECAST_URL,
            params,
            FORECAST_CACHE_MINUTES,
        )

    def fetch_historical(
        self,
        location: LocationResult,
        days: int = HISTORICAL_DAYS,
    ) -> dict[str, Any]:
        """Fetch historical weather from Open-Meteo Archive API."""

        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=max(days - 1, 1))
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "hourly": ",".join(HISTORICAL_HOURLY_VARIABLES),
            "daily": ",".join(HISTORICAL_DAILY_VARIABLES),
            "timezone": "auto",
        }
        return self._get_json(
            "historical",
            OPEN_METEO_ARCHIVE_URL,
            params,
            HISTORICAL_CACHE_MINUTES,
        )

    def fetch_air_quality(self, location: LocationResult) -> dict[str, Any]:
        """Fetch AQI and pollutant forecast data from Open-Meteo Air Quality."""

        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": ",".join(AIR_QUALITY_CURRENT_VARIABLES),
            "hourly": ",".join(AIR_QUALITY_HOURLY_VARIABLES),
            "timezone": "auto",
            "forecast_days": 5,
        }
        return self._get_json(
            "air_quality",
            OPEN_METEO_AIR_QUALITY_URL,
            params,
            AIR_QUALITY_CACHE_MINUTES,
        )

    def _get_json(
        self,
        endpoint: str,
        url: str,
        params: dict[str, Any],
        ttl_minutes: int,
    ) -> dict[str, Any]:
        """Get JSON from Open-Meteo with caching and offline fallback."""

        cache_key = self._cache_key(url, params)
        cached = self.database.get_cached_response(cache_key)
        if cached is not None:
            return cached

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            fallback = self.database.get_cached_response(cache_key, allow_expired=True)
            if fallback is not None:
                fallback["_weathervision_cached_fallback"] = True
                return fallback
            raise WeatherApiError(
                "Could not reach Open-Meteo. Check your internet connection and try again."
            ) from exc

        if data.get("error"):
            message = data.get("reason") or "Open-Meteo returned an error."
            raise WeatherApiError(message)

        self.database.set_cached_response(cache_key, endpoint, data, ttl_minutes)
        return data

    @staticmethod
    def _cache_key(url: str, params: dict[str, Any]) -> str:
        """Build a stable cache key from URL and request parameters."""

        normalized = json.dumps({"url": url, "params": params}, sort_keys=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def detect_current_location_windows(timeout_seconds: int = 9) -> LocationResult:
    """Ask Windows Location Services for the user's current coordinates.

    This does not call any IP geolocation service. If Windows Location Services
    are off, Windows will not provide coordinates and we show a friendly error.
    """

    if platform.system().lower() != "windows":
        raise WeatherApiError("Current location detection is implemented for Windows.")

    script = r"""
Add-Type -AssemblyName System.Device
$watcher = New-Object System.Device.Location.GeoCoordinateWatcher
$watcher.Start()
$deadline = [DateTime]::Now.AddSeconds(8)
while (($watcher.Status -ne 'Ready') -and ([DateTime]::Now -lt $deadline)) {
    Start-Sleep -Milliseconds 250
}
$location = $watcher.Position.Location
if ($location.IsUnknown) {
    exit 2
}
Write-Output ("{0},{1}" -f $location.Latitude, $location.Longitude)
"""

    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WeatherApiError("Windows could not provide the current location.") from exc

    if completed.returncode != 0 or not completed.stdout.strip():
        raise WeatherApiError(
            "Turn on Windows Location Services, then try Current Location again."
        )

    try:
        latitude_text, longitude_text = completed.stdout.strip().split(",", 1)
        latitude = float(latitude_text)
        longitude = float(longitude_text)
    except ValueError as exc:
        raise WeatherApiError("Windows returned an unreadable location.") from exc

    return LocationResult(
        name="Current Location",
        country=None,
        latitude=latitude,
        longitude=longitude,
        timezone=None,
        admin1=None,
    )
