"""Weather analytics helpers.

Open-Meteo returns JSON. Charts and exports are easier when the same data is in
tables, so this module converts JSON into pandas DataFrames and calculates
simple trends from the real values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from config import weather_label
from weather_api import WeatherBundle


def _frame_from_section(payload: dict[str, Any], section: str, time_column: str) -> pd.DataFrame:
    """Convert one Open-Meteo JSON section into a pandas table."""

    section_data = payload.get(section) or {}
    if not section_data or time_column not in section_data:
        return pd.DataFrame()

    frame = pd.DataFrame(section_data)
    frame[time_column] = pd.to_datetime(frame[time_column])
    return frame


def _safe_number(value: Any) -> float | None:
    """Return a float only when the value is a real number."""

    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: Any, suffix: str = "", decimals: int = 1) -> str:
    number = _safe_number(value)
    if number is None:
        return "Unavailable"
    if decimals == 0:
        return f"{number:.0f}{suffix}"
    return f"{number:.{decimals}f}{suffix}"


@dataclass
class AnalyticsFrames:
    """Named DataFrames used throughout the UI, charts, and exporters."""

    hourly: pd.DataFrame
    daily: pd.DataFrame
    historical_hourly: pd.DataFrame
    historical_daily: pd.DataFrame
    air_quality_hourly: pd.DataFrame


class WeatherAnalytics:
    """Calculates dashboard numbers from real Open-Meteo data."""

    def __init__(self, bundle: WeatherBundle) -> None:
        self.bundle = bundle
        self.frames = AnalyticsFrames(
            hourly=_frame_from_section(bundle.forecast, "hourly", "time"),
            daily=_frame_from_section(bundle.forecast, "daily", "time"),
            historical_hourly=_frame_from_section(bundle.historical, "hourly", "time"),
            historical_daily=_frame_from_section(bundle.historical, "daily", "time"),
            air_quality_hourly=_frame_from_section(bundle.air_quality, "hourly", "time"),
        )

    def current_conditions(self) -> dict[str, Any]:
        """Return current weather values exactly as supplied by Open-Meteo."""

        current = dict(self.bundle.forecast.get("current") or {})
        current_units = self.bundle.forecast.get("current_units") or {}
        code = current.get("weather_code")
        current["weather_label"] = weather_label(code)
        current["units"] = current_units
        return current

    def air_quality_current(self) -> dict[str, Any]:
        """Return current AQI values from Open-Meteo Air Quality."""

        current = dict(self.bundle.air_quality.get("current") or {})
        current["units"] = self.bundle.air_quality.get("current_units") or {}
        return current

    def summary_metrics(self) -> dict[str, str]:
        """Build the compact metric cards shown on the dashboard."""

        current = self.current_conditions()
        daily = self.frames.daily
        historical_daily = self.frames.historical_daily
        aq_current = self.air_quality_current()

        today_high = daily["temperature_2m_max"].iloc[0] if "temperature_2m_max" in daily else None
        today_low = daily["temperature_2m_min"].iloc[0] if "temperature_2m_min" in daily else None
        rain_probability = (
            daily["precipitation_probability_max"].iloc[0]
            if "precipitation_probability_max" in daily
            else None
        )
        uv_index = daily["uv_index_max"].iloc[0] if "uv_index_max" in daily else None

        history_average = None
        if "temperature_2m_mean" in historical_daily and not historical_daily.empty:
            history_average = historical_daily["temperature_2m_mean"].mean()

        return {
            "Temperature": _format_number(current.get("temperature_2m"), " C"),
            "Feels Like": _format_number(current.get("apparent_temperature"), " C"),
            "Humidity": _format_number(current.get("relative_humidity_2m"), "%", 0),
            "Wind": _format_number(current.get("wind_speed_10m"), " km/h"),
            "Today High": _format_number(today_high, " C"),
            "Today Low": _format_number(today_low, " C"),
            "Rain Chance": _format_number(rain_probability, "%", 0),
            "UV Index": _format_number(uv_index, "", 1),
            "Pressure": _format_number(current.get("pressure_msl"), " hPa", 0),
            "AQI": _format_number(aq_current.get("european_aqi"), "", 0),
            "45-Day Avg": _format_number(history_average, " C"),
            "Trend": self.temperature_trend_label(),
        }

    def temperature_trend_label(self) -> str:
        """Describe whether historical mean temperatures are rising or falling."""

        frame = self.frames.historical_daily
        if frame.empty or "temperature_2m_mean" not in frame:
            return "Unavailable"

        clean = frame.dropna(subset=["temperature_2m_mean"]).copy()
        if len(clean) < 3:
            return "Not enough data"

        x_values = np.arange(len(clean))
        y_values = clean["temperature_2m_mean"].astype(float).to_numpy()
        slope = float(np.polyfit(x_values, y_values, 1)[0])

        if slope > 0.05:
            direction = "warming"
        elif slope < -0.05:
            direction = "cooling"
        else:
            direction = "stable"
        return f"{direction.title()} ({slope:+.2f} C/day)"

    def weekly_forecast_rows(self) -> list[dict[str, Any]]:
        """Return one dictionary per day for the 7-day forecast cards."""

        daily = self.frames.daily
        if daily.empty:
            return []

        rows: list[dict[str, Any]] = []
        for _, row in daily.head(7).iterrows():
            rows.append(
                {
                    "date": row["time"].strftime("%a, %b %d"),
                    "weather_code": row.get("weather_code"),
                    "label": weather_label(row.get("weather_code")),
                    "high": _format_number(row.get("temperature_2m_max"), " C"),
                    "low": _format_number(row.get("temperature_2m_min"), " C"),
                    "rain": _format_number(row.get("precipitation_probability_max"), "%", 0),
                    "wind": _format_number(row.get("wind_speed_10m_max"), " km/h"),
                }
            )
        return rows

    def hourly_rows(self, limit: int = 24) -> list[dict[str, Any]]:
        """Return upcoming hourly forecast rows for the dashboard table."""

        hourly = self.frames.hourly
        if hourly.empty:
            return []

        now = pd.Timestamp.now()
        upcoming = hourly[hourly["time"] >= now].head(limit)
        if upcoming.empty:
            upcoming = hourly.head(limit)

        rows: list[dict[str, Any]] = []
        for _, row in upcoming.iterrows():
            rows.append(
                {
                    "time": row["time"].strftime("%a %H:%M"),
                    "temperature": _format_number(row.get("temperature_2m"), " C"),
                    "feels_like": _format_number(row.get("apparent_temperature"), " C"),
                    "humidity": _format_number(row.get("relative_humidity_2m"), "%", 0),
                    "rain": _format_number(row.get("precipitation_probability"), "%", 0),
                    "wind": _format_number(row.get("wind_speed_10m"), " km/h"),
                    "condition": weather_label(row.get("weather_code")),
                }
            )
        return rows

    def export_frames(self) -> dict[str, pd.DataFrame]:
        """Return copies of all tables used by export functions."""

        return {
            "hourly_forecast": self.frames.hourly.copy(),
            "daily_forecast": self.frames.daily.copy(),
            "historical_hourly": self.frames.historical_hourly.copy(),
            "historical_daily": self.frames.historical_daily.copy(),
            "air_quality": self.frames.air_quality_hourly.copy(),
        }

    def report_summary_lines(self) -> list[str]:
        """Plain text summary used in PDF export."""

        current = self.current_conditions()
        location = self.bundle.location.display_name
        metrics = self.summary_metrics()
        return [
            f"Location: {location}",
            f"Condition: {current.get('weather_label', 'Unavailable')}",
            f"Current temperature: {metrics['Temperature']}",
            f"Feels like: {metrics['Feels Like']}",
            f"Humidity: {metrics['Humidity']}",
            f"Wind speed: {metrics['Wind']}",
            f"Pressure: {metrics['Pressure']}",
            f"Air quality index: {metrics['AQI']}",
            f"Historical temperature trend: {metrics['Trend']}",
        ]
