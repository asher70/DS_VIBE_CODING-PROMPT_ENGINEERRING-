"""Charts for the WeatherVision Pro analytics dashboard.

The app uses Matplotlib for embedded desktop charts and Plotly for a separate
interactive HTML dashboard with zoom and hover tooltips. Both chart systems use
the same real Open-Meteo tables from `analytics.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:  # The README and requirements explain how to install it.
    go = None
    make_subplots = None

from analytics import WeatherAnalytics
from config import PALETTES


ChartBuilder = Callable[[], Figure]


class ChartFactory:
    """Build all dashboard charts from one WeatherAnalytics object."""

    def __init__(self, analytics: WeatherAnalytics, dark_mode: bool = False) -> None:
        self.analytics = analytics
        self.frames = analytics.frames
        self.palette = PALETTES["dark" if dark_mode else "light"]

    def chart_definitions(self) -> list[tuple[str, str, ChartBuilder]]:
        """Return the 15 required charts in a stable order."""

        return [
            ("hourly_temperature", "Hourly Temperature Line Chart", self.hourly_temperature),
            ("weekly_temperature", "Weekly Temperature Trend", self.weekly_temperature),
            ("humidity_area", "Humidity Area Chart", self.humidity_area),
            ("wind_speed", "Wind Speed Line Graph", self.wind_speed),
            ("rain_probability", "Rain Probability Bar Chart", self.rain_probability),
            ("uv_index", "UV Index Chart", self.uv_index),
            ("pressure_trend", "Pressure Trend Chart", self.pressure_trend),
            ("sunrise_sunset", "Sunrise/Sunset Comparison", self.sunrise_sunset),
            ("temperature_heatmap", "Temperature Heatmap", self.temperature_heatmap),
            ("precipitation_forecast", "Precipitation Forecast Chart", self.precipitation_forecast),
            ("air_quality", "Air Quality Graph", self.air_quality),
            ("visibility_trend", "Visibility Trend Chart", self.visibility_trend),
            ("forecast_comparison", "Multi-Day Forecast Comparison", self.forecast_comparison),
            ("feels_like", "Feels Like vs Actual Temperature", self.feels_like_vs_actual),
            ("historical_trend", "Historical Weather Trend Graph", self.historical_trend),
        ]

    def _figure(self, title: str, figsize: tuple[float, float] = (8.8, 3.8)) -> tuple[Figure, plt.Axes]:
        fig, ax = plt.subplots(figsize=figsize, dpi=105)
        fig.patch.set_facecolor(self.palette["chart_bg"])
        ax.set_facecolor(self.palette["chart_bg"])
        ax.set_title(title, loc="left", color=self.palette["text"], fontsize=12, fontweight="bold")
        ax.tick_params(colors=self.palette["muted"], labelsize=8)
        ax.grid(True, color=self.palette["grid"], linewidth=0.7, alpha=0.65)
        for spine in ax.spines.values():
            spine.set_color(self.palette["grid"])
        return fig, ax

    def _finish(self, fig: Figure, ax: plt.Axes, ylabel: str | None = None) -> Figure:
        if ylabel:
            ax.set_ylabel(ylabel, color=self.palette["muted"])
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=7))
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
        fig.tight_layout(pad=1.6)
        return fig

    def _empty_figure(self, title: str, message: str = "Open-Meteo did not return this data.") -> Figure:
        fig, ax = self._figure(title)
        ax.text(
            0.5,
            0.5,
            message,
            transform=ax.transAxes,
            ha="center",
            va="center",
            color=self.palette["muted"],
            fontsize=11,
        )
        ax.set_xticks([])
        ax.set_yticks([])
        fig.tight_layout(pad=1.6)
        return fig

    def _upcoming_hourly(self, hours: int = 72) -> pd.DataFrame:
        hourly = self.frames.hourly
        if hourly.empty or "time" not in hourly:
            return pd.DataFrame()
        now = pd.Timestamp.now()
        upcoming = hourly[hourly["time"] >= now].head(hours).copy()
        if upcoming.empty:
            upcoming = hourly.head(hours).copy()
        return upcoming

    def hourly_temperature(self) -> Figure:
        frame = self._upcoming_hourly(72)
        if frame.empty or "temperature_2m" not in frame:
            return self._empty_figure("Hourly Temperature Line Chart")
        fig, ax = self._figure("Hourly Temperature Line Chart")
        ax.plot(frame["time"], frame["temperature_2m"], color=self.palette["accent"], linewidth=2.4)
        ax.fill_between(frame["time"], frame["temperature_2m"], alpha=0.12, color=self.palette["accent"])
        return self._finish(fig, ax, "Temperature (C)")

    def weekly_temperature(self) -> Figure:
        daily = self.frames.daily
        required = {"time", "temperature_2m_max", "temperature_2m_min"}
        if daily.empty or not required.issubset(daily.columns):
            return self._empty_figure("Weekly Temperature Trend")
        fig, ax = self._figure("Weekly Temperature Trend")
        ax.plot(daily["time"], daily["temperature_2m_max"], marker="o", color=self.palette["danger"], label="High")
        ax.plot(daily["time"], daily["temperature_2m_min"], marker="o", color=self.palette["accent"], label="Low")
        ax.legend(facecolor=self.palette["chart_bg"], labelcolor=self.palette["text"])
        return self._finish(fig, ax, "Temperature (C)")

    def humidity_area(self) -> Figure:
        frame = self._upcoming_hourly(72)
        if frame.empty or "relative_humidity_2m" not in frame:
            return self._empty_figure("Humidity Area Chart")
        fig, ax = self._figure("Humidity Area Chart")
        ax.fill_between(frame["time"], frame["relative_humidity_2m"], color=self.palette["accent_2"], alpha=0.25)
        ax.plot(frame["time"], frame["relative_humidity_2m"], color=self.palette["accent_2"], linewidth=2)
        ax.set_ylim(0, 100)
        return self._finish(fig, ax, "Humidity (%)")

    def wind_speed(self) -> Figure:
        frame = self._upcoming_hourly(72)
        if frame.empty or "wind_speed_10m" not in frame:
            return self._empty_figure("Wind Speed Line Graph")
        fig, ax = self._figure("Wind Speed Line Graph")
        ax.plot(frame["time"], frame["wind_speed_10m"], color="#8b5cf6", linewidth=2)
        if "wind_gusts_10m" in frame:
            ax.plot(frame["time"], frame["wind_gusts_10m"], color=self.palette["warning"], linewidth=1.5, alpha=0.75, label="Gusts")
            ax.legend(facecolor=self.palette["chart_bg"], labelcolor=self.palette["text"])
        return self._finish(fig, ax, "Wind (km/h)")

    def rain_probability(self) -> Figure:
        frame = self._upcoming_hourly(48)
        if frame.empty or "precipitation_probability" not in frame:
            return self._empty_figure("Rain Probability Bar Chart")
        fig, ax = self._figure("Rain Probability Bar Chart")
        ax.bar(frame["time"], frame["precipitation_probability"], color=self.palette["accent"], width=0.03)
        ax.set_ylim(0, 100)
        return self._finish(fig, ax, "Probability (%)")

    def uv_index(self) -> Figure:
        daily = self.frames.daily
        if daily.empty or "uv_index_max" not in daily:
            return self._empty_figure("UV Index Chart")
        fig, ax = self._figure("UV Index Chart")
        colors = np.where(daily["uv_index_max"] >= 8, self.palette["danger"], self.palette["warning"])
        ax.bar(daily["time"], daily["uv_index_max"], color=colors, width=0.6)
        return self._finish(fig, ax, "UV Index")

    def pressure_trend(self) -> Figure:
        frame = self._upcoming_hourly(72)
        column = "pressure_msl" if "pressure_msl" in frame else "surface_pressure"
        if frame.empty or column not in frame:
            return self._empty_figure("Pressure Trend Chart")
        fig, ax = self._figure("Pressure Trend Chart")
        ax.plot(frame["time"], frame[column], color="#14b8a6", linewidth=2.2)
        return self._finish(fig, ax, "Pressure (hPa)")

    def sunrise_sunset(self) -> Figure:
        daily = self.frames.daily
        required = {"time", "sunrise", "sunset"}
        if daily.empty or not required.issubset(daily.columns):
            return self._empty_figure("Sunrise/Sunset Comparison")
        sunrise = pd.to_datetime(daily["sunrise"])
        sunset = pd.to_datetime(daily["sunset"])
        sunrise_hour = sunrise.dt.hour + sunrise.dt.minute / 60
        sunset_hour = sunset.dt.hour + sunset.dt.minute / 60
        fig, ax = self._figure("Sunrise/Sunset Comparison")
        ax.plot(daily["time"], sunrise_hour, marker="o", color=self.palette["warning"], label="Sunrise")
        ax.plot(daily["time"], sunset_hour, marker="o", color="#f97316", label="Sunset")
        ax.set_yticks(range(0, 25, 3))
        ax.legend(facecolor=self.palette["chart_bg"], labelcolor=self.palette["text"])
        return self._finish(fig, ax, "Hour of day")

    def temperature_heatmap(self) -> Figure:
        frame = self._upcoming_hourly(24 * 7)
        if frame.empty or "temperature_2m" not in frame:
            return self._empty_figure("Temperature Heatmap")
        heat = frame.copy()
        heat["date"] = heat["time"].dt.strftime("%a %m-%d")
        heat["hour"] = heat["time"].dt.hour
        pivot = heat.pivot_table(index="date", columns="hour", values="temperature_2m", aggfunc="mean")
        if pivot.empty:
            return self._empty_figure("Temperature Heatmap")
        fig, ax = self._figure("Temperature Heatmap", figsize=(8.8, 4.2))
        image = ax.imshow(pivot, aspect="auto", cmap="coolwarm")
        ax.set_yticks(np.arange(len(pivot.index)))
        ax.set_yticklabels(pivot.index, color=self.palette["muted"])
        ax.set_xticks(np.arange(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns, rotation=0, color=self.palette["muted"])
        ax.set_xlabel("Hour", color=self.palette["muted"])
        colorbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.03)
        colorbar.ax.tick_params(colors=self.palette["muted"])
        fig.tight_layout(pad=1.6)
        return fig

    def precipitation_forecast(self) -> Figure:
        frame = self._upcoming_hourly(72)
        if frame.empty or "precipitation" not in frame:
            return self._empty_figure("Precipitation Forecast Chart")
        fig, ax = self._figure("Precipitation Forecast Chart")
        ax.bar(frame["time"], frame["precipitation"], color="#2563eb", width=0.03)
        return self._finish(fig, ax, "Precipitation (mm)")

    def air_quality(self) -> Figure:
        frame = self.frames.air_quality_hourly
        if frame.empty or "time" not in frame:
            return self._empty_figure("Air Quality Graph")
        upcoming = frame[frame["time"] >= pd.Timestamp.now()].head(96)
        if upcoming.empty:
            upcoming = frame.head(96)
        fig, ax = self._figure("Air Quality Graph")
        if "european_aqi" in upcoming:
            ax.plot(upcoming["time"], upcoming["european_aqi"], color=self.palette["danger"], linewidth=2, label="European AQI")
        if "pm2_5" in upcoming:
            ax.plot(upcoming["time"], upcoming["pm2_5"], color=self.palette["warning"], linewidth=1.8, label="PM2.5")
        ax.legend(facecolor=self.palette["chart_bg"], labelcolor=self.palette["text"])
        return self._finish(fig, ax, "AQI / micrograms per cubic meter")

    def visibility_trend(self) -> Figure:
        frame = self._upcoming_hourly(72)
        if frame.empty or "visibility" not in frame:
            return self._empty_figure("Visibility Trend Chart")
        fig, ax = self._figure("Visibility Trend Chart")
        visibility_km = frame["visibility"] / 1000.0
        ax.plot(frame["time"], visibility_km, color="#06b6d4", linewidth=2.2)
        return self._finish(fig, ax, "Visibility (km)")

    def forecast_comparison(self) -> Figure:
        daily = self.frames.daily
        required = {"time", "temperature_2m_max", "temperature_2m_min", "precipitation_sum"}
        if daily.empty or not required.issubset(daily.columns):
            return self._empty_figure("Multi-Day Forecast Comparison")
        fig, ax = self._figure("Multi-Day Forecast Comparison")
        average_temperature = (daily["temperature_2m_max"] + daily["temperature_2m_min"]) / 2
        ax.bar(daily["time"], average_temperature, color=self.palette["accent"], width=0.55, label="Avg temp")
        ax2 = ax.twinx()
        ax2.plot(daily["time"], daily["precipitation_sum"], color=self.palette["warning"], marker="o", label="Rain")
        ax2.tick_params(colors=self.palette["muted"], labelsize=8)
        ax2.set_ylabel("Precipitation (mm)", color=self.palette["muted"])
        ax.set_ylabel("Average temp (C)", color=self.palette["muted"])
        fig.tight_layout(pad=1.6)
        return fig

    def feels_like_vs_actual(self) -> Figure:
        frame = self._upcoming_hourly(72)
        required = {"time", "temperature_2m", "apparent_temperature"}
        if frame.empty or not required.issubset(frame.columns):
            return self._empty_figure("Feels Like vs Actual Temperature")
        fig, ax = self._figure("Feels Like vs Actual Temperature")
        ax.plot(frame["time"], frame["temperature_2m"], color=self.palette["accent"], linewidth=2, label="Actual")
        ax.plot(frame["time"], frame["apparent_temperature"], color=self.palette["danger"], linewidth=2, label="Feels like")
        ax.legend(facecolor=self.palette["chart_bg"], labelcolor=self.palette["text"])
        return self._finish(fig, ax, "Temperature (C)")

    def historical_trend(self) -> Figure:
        daily = self.frames.historical_daily
        if daily.empty or "temperature_2m_mean" not in daily:
            return self._empty_figure("Historical Weather Trend Graph")
        fig, ax = self._figure("Historical Weather Trend Graph")
        ax.plot(daily["time"], daily["temperature_2m_mean"], color=self.palette["accent"], linewidth=2.2, label="Mean")
        if "temperature_2m_max" in daily:
            ax.plot(daily["time"], daily["temperature_2m_max"], color=self.palette["danger"], linewidth=1.3, alpha=0.7, label="High")
        if "temperature_2m_min" in daily:
            ax.plot(daily["time"], daily["temperature_2m_min"], color="#60a5fa", linewidth=1.3, alpha=0.7, label="Low")
        ax.legend(facecolor=self.palette["chart_bg"], labelcolor=self.palette["text"])
        return self._finish(fig, ax, "Temperature (C)")


def build_plotly_dashboard(analytics: WeatherAnalytics, output_path: Path) -> Path:
    """Create a self-contained interactive Plotly HTML dashboard."""

    if go is None or make_subplots is None:
        raise RuntimeError("Plotly is not installed. Run: pip install plotly")

    frames = analytics.frames
    hourly = frames.hourly
    daily = frames.daily
    historical = frames.historical_daily
    air = frames.air_quality_hourly

    fig = make_subplots(
        rows=5,
        cols=3,
        subplot_titles=[
            "Hourly Temperature",
            "Weekly Temperature",
            "Humidity",
            "Wind Speed",
            "Rain Probability",
            "UV Index",
            "Pressure",
            "Sunrise/Sunset",
            "Temperature Heatmap",
            "Precipitation",
            "Air Quality",
            "Visibility",
            "Forecast Comparison",
            "Feels Like vs Actual",
            "Historical Trend",
        ],
        specs=[
            [{}, {}, {}],
            [{}, {}, {}],
            [{}, {}, {"type": "heatmap"}],
            [{}, {}, {}],
            [{}, {}, {}],
        ],
        vertical_spacing=0.08,
    )

    upcoming = hourly[hourly["time"] >= pd.Timestamp.now()].head(24 * 7) if not hourly.empty else hourly
    if upcoming.empty:
        upcoming = hourly.head(24 * 7)

    def add_line(row: int, col: int, frame: pd.DataFrame, y: str, name: str, color: str) -> None:
        if not frame.empty and y in frame:
            fig.add_trace(
                go.Scatter(
                    x=frame["time"],
                    y=frame[y],
                    mode="lines",
                    name=name,
                    line={"color": color, "width": 2},
                    hovertemplate="%{x}<br>%{y}<extra>" + name + "</extra>",
                ),
                row=row,
                col=col,
            )

    add_line(1, 1, upcoming, "temperature_2m", "Temperature", "#0ea5e9")
    if not daily.empty:
        add_line(1, 2, daily, "temperature_2m_max", "High", "#ef4444")
        add_line(1, 2, daily, "temperature_2m_min", "Low", "#3b82f6")
    add_line(1, 3, upcoming, "relative_humidity_2m", "Humidity", "#22c55e")
    add_line(2, 1, upcoming, "wind_speed_10m", "Wind", "#8b5cf6")
    if not upcoming.empty and "precipitation_probability" in upcoming:
        fig.add_trace(go.Bar(x=upcoming["time"], y=upcoming["precipitation_probability"], name="Rain %", marker_color="#0ea5e9"), row=2, col=2)
    if not daily.empty and "uv_index_max" in daily:
        fig.add_trace(go.Bar(x=daily["time"], y=daily["uv_index_max"], name="UV", marker_color="#f59e0b"), row=2, col=3)
    add_line(3, 1, upcoming, "pressure_msl", "Pressure", "#14b8a6")
    if not daily.empty and {"sunrise", "sunset"}.issubset(daily.columns):
        sunrise = pd.to_datetime(daily["sunrise"]).dt.hour + pd.to_datetime(daily["sunrise"]).dt.minute / 60
        sunset = pd.to_datetime(daily["sunset"]).dt.hour + pd.to_datetime(daily["sunset"]).dt.minute / 60
        fig.add_trace(go.Scatter(x=daily["time"], y=sunrise, name="Sunrise", mode="lines+markers", line_color="#f59e0b"), row=3, col=2)
        fig.add_trace(go.Scatter(x=daily["time"], y=sunset, name="Sunset", mode="lines+markers", line_color="#f97316"), row=3, col=2)
    if not upcoming.empty and "temperature_2m" in upcoming:
        heat = upcoming.copy()
        heat["date"] = heat["time"].dt.strftime("%a %m-%d")
        heat["hour"] = heat["time"].dt.hour
        pivot = heat.pivot_table(index="date", columns="hour", values="temperature_2m", aggfunc="mean")
        fig.add_trace(go.Heatmap(z=pivot.values, x=pivot.columns, y=pivot.index, colorscale="RdBu_r", name="Heatmap"), row=3, col=3)
    if not upcoming.empty and "precipitation" in upcoming:
        fig.add_trace(go.Bar(x=upcoming["time"], y=upcoming["precipitation"], name="Precipitation", marker_color="#2563eb"), row=4, col=1)
    if not air.empty:
        aq = air[air["time"] >= pd.Timestamp.now()].head(96)
        if aq.empty:
            aq = air.head(96)
        add_line(4, 2, aq, "european_aqi", "AQI", "#ef4444")
        add_line(4, 2, aq, "pm2_5", "PM2.5", "#f59e0b")
    if not upcoming.empty and "visibility" in upcoming:
        visibility = upcoming.copy()
        visibility["visibility_km"] = visibility["visibility"] / 1000.0
        add_line(4, 3, visibility, "visibility_km", "Visibility km", "#06b6d4")
    if not daily.empty and {"temperature_2m_max", "temperature_2m_min"}.issubset(daily.columns):
        comparison = daily.copy()
        comparison["average_temperature"] = (comparison["temperature_2m_max"] + comparison["temperature_2m_min"]) / 2
        fig.add_trace(go.Bar(x=comparison["time"], y=comparison["average_temperature"], name="Avg temp", marker_color="#0ea5e9"), row=5, col=1)
    add_line(5, 2, upcoming, "temperature_2m", "Actual", "#0ea5e9")
    add_line(5, 2, upcoming, "apparent_temperature", "Feels like", "#ef4444")
    add_line(5, 3, historical, "temperature_2m_mean", "Historical mean", "#0ea5e9")

    fig.update_layout(
        title=f"WeatherVision Pro Interactive Dashboard - {analytics.bundle.location.display_name}",
        height=1850,
        template="plotly_white",
        hovermode="x unified",
        showlegend=True,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path), include_plotlyjs=True, full_html=True)
    return output_path
