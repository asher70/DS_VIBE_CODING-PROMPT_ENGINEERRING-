"""Export tools for reports, spreadsheets, CSV files, and chart snapshots."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

from analytics import WeatherAnalytics
from charts import ChartFactory
from config import EXPORT_DIR
from database import WeatherDatabase


def _safe_filename(text: str) -> str:
    """Turn a city name into a safe file-name piece."""

    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
    return cleaned.strip("_") or "weather"


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class WeatherExporter:
    """Writes local export files and records them in SQLite."""

    def __init__(self, database: WeatherDatabase, export_dir: Path = EXPORT_DIR) -> None:
        self.database = database
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_csv_bundle(self, analytics: WeatherAnalytics) -> list[Path]:
        """Export every available weather table as separate CSV files."""

        city = analytics.bundle.location.display_name
        folder = self.export_dir / f"{_safe_filename(city)}_csv_{_timestamp()}"
        folder.mkdir(parents=True, exist_ok=True)

        paths: list[Path] = []
        for name, frame in analytics.export_frames().items():
            if frame.empty:
                continue
            path = folder / f"{name}.csv"
            frame.to_csv(path, index=False)
            paths.append(path)

        self.database.log_export("CSV", str(folder), city)
        return paths

    def export_excel(self, analytics: WeatherAnalytics) -> Path:
        """Export all weather tables into one Excel workbook."""

        city = analytics.bundle.location.display_name
        path = self.export_dir / f"{_safe_filename(city)}_weather_{_timestamp()}.xlsx"

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for name, frame in analytics.export_frames().items():
                if frame.empty:
                    continue
                sheet_name = name[:31]
                frame.to_excel(writer, sheet_name=sheet_name, index=False)

        self.database.log_export("Excel", str(path), city)
        return path

    def export_pdf_report(self, analytics: WeatherAnalytics, dark_mode: bool = False) -> Path:
        """Create a PDF report with summary text and all charts."""

        city = analytics.bundle.location.display_name
        path = self.export_dir / f"{_safe_filename(city)}_report_{_timestamp()}.pdf"
        chart_factory = ChartFactory(analytics, dark_mode=dark_mode)

        with PdfPages(path) as pdf:
            summary_fig = plt.figure(figsize=(11, 8.5), dpi=120)
            summary_fig.patch.set_facecolor("white")
            ax = summary_fig.add_subplot(111)
            ax.axis("off")
            ax.text(
                0.05,
                0.94,
                "WeatherVision Pro Weather Report",
                fontsize=22,
                fontweight="bold",
                color="#172033",
            )
            ax.text(
                0.05,
                0.89,
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                fontsize=10,
                color="#6c788a",
            )
            y = 0.80
            for line in analytics.report_summary_lines():
                ax.text(0.06, y, line, fontsize=13, color="#18202f")
                y -= 0.055
            ax.text(
                0.06,
                0.12,
                "Data source: Open-Meteo Forecast, Historical Weather, Geocoding, and Air Quality APIs.",
                fontsize=10,
                color="#6c788a",
            )
            pdf.savefig(summary_fig, bbox_inches="tight")
            plt.close(summary_fig)

            for _, _, builder in chart_factory.chart_definitions():
                fig = builder()
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

        self.database.log_export("PDF", str(path), city)
        return path

    def export_chart_snapshots(self, analytics: WeatherAnalytics, dark_mode: bool = False) -> list[Path]:
        """Save every dashboard chart as a PNG image."""

        city = analytics.bundle.location.display_name
        folder = self.export_dir / f"{_safe_filename(city)}_chart_png_{_timestamp()}"
        folder.mkdir(parents=True, exist_ok=True)
        chart_factory = ChartFactory(analytics, dark_mode=dark_mode)

        paths: list[Path] = []
        for chart_id, _, builder in chart_factory.chart_definitions():
            fig = builder()
            path = folder / f"{chart_id}.png"
            fig.savefig(path, dpi=160, bbox_inches="tight")
            plt.close(fig)
            paths.append(path)

        self.database.log_export("PNG Charts", str(folder), city)
        return paths
