"""Tkinter and ttkbootstrap user interface for WeatherVision Pro."""

from __future__ import annotations

import os
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk

import ttkbootstrap as tb
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from PIL import Image, ImageTk

from analytics import WeatherAnalytics
from charts import ChartFactory, build_plotly_dashboard
from config import (
    APP_ICON_PATH,
    APP_ICON_PNG_PATH,
    APP_NAME,
    DARK_THEME,
    DEFAULT_AUTO_REFRESH_MINUTES,
    DEFAULT_CITY,
    EXPORT_DIR,
    ICON_DIR,
    LIGHT_THEME,
    PALETTES,
    icon_name_for_weather,
)
from database import WeatherDatabase
from export import WeatherExporter
from weather_api import (
    LocationResult,
    OpenMeteoClient,
    WeatherApiError,
    WeatherBundle,
    detect_current_location_windows,
)


class ScrollableFrame(ttk.Frame):
    """A frame with a vertical scrollbar.

    Tkinter frames do not scroll by themselves. This helper puts a normal frame
    inside a canvas, and the canvas handles scrolling.
    """

    def __init__(self, parent: tk.Widget, background: str) -> None:
        super().__init__(parent)
        self.canvas = tk.Canvas(parent, bg=background, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=background)

        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_inner_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


def center_window(window: tk.Tk | tk.Toplevel, width: int, height: int) -> None:
    """Place a window in the center of the screen."""

    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = max((screen_width - width) // 2, 0)
    y = max((screen_height - height) // 2, 0)
    window.geometry(f"{width}x{height}+{x}+{y}")


def show_splash_screen(parent: tk.Tk) -> None:
    """Show a short startup splash screen as a Toplevel child of the main window.

    IMPORTANT: The parent window must already exist (and be withdrawn) before
    calling this function.  Using a Toplevel instead of a second tk.Tk() avoids
    the Python 3.14 / ttkbootstrap bug where ttkbootstrap's singleton Style
    keeps a reference to the first Tk instance after it is destroyed.
    """

    splash = tk.Toplevel(parent)
    splash.overrideredirect(True)
    splash.configure(bg="#0d1117")
    center_window(splash, 520, 300)

    try:
        splash.attributes("-alpha", 0.0)
        if APP_ICON_PATH.exists():
            splash.iconbitmap(str(APP_ICON_PATH))
    except tk.TclError:
        pass

    card = tk.Frame(splash, bg="#111827", padx=28, pady=24)
    card.pack(fill="both", expand=True, padx=16, pady=16)

    if APP_ICON_PNG_PATH.exists():
        try:
            image = Image.open(APP_ICON_PNG_PATH).resize((82, 82))
            photo = ImageTk.PhotoImage(image)
            icon_label = tk.Label(card, image=photo, bg="#111827")
            icon_label.image = photo  # keep a reference so GC doesn't collect it
            icon_label.pack(pady=(8, 12))
        except Exception:
            pass

    tk.Label(
        card,
        text=APP_NAME,
        bg="#111827",
        fg="#f8fafc",
        font=("Segoe UI", 22, "bold"),
    ).pack()
    tk.Label(
        card,
        text="Loading real Open-Meteo weather analytics",
        bg="#111827",
        fg="#aeb8c7",
        font=("Segoe UI", 10),
    ).pack(pady=(6, 18))

    progress = ttk.Progressbar(card, mode="indeterminate", length=360)
    progress.pack()
    progress.start(14)

    for alpha in [i / 10 for i in range(1, 11)]:
        try:
            splash.attributes("-alpha", alpha)
        except tk.TclError:
            break
        splash.update()
        time.sleep(0.025)

    splash.update()
    time.sleep(0.45)
    splash.destroy()


class WeatherVisionApp(tb.Window):
    """Main Windows desktop application."""

    def __init__(self) -> None:
        self.database = WeatherDatabase()
        self.theme_mode = self.database.get_setting("theme_mode", "light")
        theme_name = DARK_THEME if self.theme_mode == "dark" else LIGHT_THEME
        super().__init__(themename=theme_name)

        self.client = OpenMeteoClient(self.database)
        self.exporter = WeatherExporter(self.database)
        self.palette = PALETTES[self.theme_mode]
        self.bundle: WeatherBundle | None = None
        self.analytics: WeatherAnalytics | None = None
        self.current_page = "dashboard"
        self.loading = False
        self.auto_refresh_job: str | None = None
        self.image_cache: dict[str, ImageTk.PhotoImage] = {}

        self.auto_refresh_var = tk.BooleanVar(
            value=bool(self.database.get_setting("auto_refresh_enabled", True))
        )
        self.refresh_minutes_var = tk.IntVar(
            value=int(self.database.get_setting("refresh_minutes", DEFAULT_AUTO_REFRESH_MINUTES))
        )
        self.search_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready")

        self._setup_window()
        self._build_shell()
        self.after(350, self._load_initial_city)

    def _setup_window(self) -> None:
        self.title(APP_NAME)
        center_window(self, 1280, 820)
        self.minsize(1060, 700)
        self.resizable(True, True)
        try:
            if APP_ICON_PATH.exists():
                self.iconbitmap(str(APP_ICON_PATH))
        except tk.TclError:
            pass
        self.bind("<F11>", lambda _event: self.attributes("-fullscreen", True))
        self.bind("<Escape>", lambda _event: self.attributes("-fullscreen", False))

    def _build_shell(self) -> None:
        """Create the permanent sidebar, topbar, and page area."""

        for child in self.winfo_children():
            child.destroy()

        self.configure(bg=self.palette["bg"])
        self.main = tk.Frame(self, bg=self.palette["bg"])
        self.main.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(self.main, bg=self.palette["sidebar"], width=238)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.body = tk.Frame(self.main, bg=self.palette["bg"])
        self.body.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        self._build_topbar()
        self.page_host = tk.Frame(self.body, bg=self.palette["bg"])
        self.page_host.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.show_page(self.current_page)

    def _build_sidebar(self) -> None:
        logo_frame = tk.Frame(self.sidebar, bg=self.palette["sidebar"])
        logo_frame.pack(fill="x", padx=18, pady=(22, 18))

        logo = self._load_icon("weather_icon.png", 52)
        if logo:
            tk.Label(logo_frame, image=logo, bg=self.palette["sidebar"]).pack(side="left", padx=(0, 10))
        title_box = tk.Frame(logo_frame, bg=self.palette["sidebar"])
        title_box.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_box,
            text="WeatherVision",
            bg=self.palette["sidebar"],
            fg="#ffffff",
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            title_box,
            text="Pro",
            bg=self.palette["sidebar"],
            fg="#8dd8ff",
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x")

        self.nav_buttons: dict[str, tk.Button] = {}
        nav_items = [
            ("dashboard", "Dashboard"),
            ("charts", "Charts"),
            ("historical", "Historical"),
            ("exports", "Exports"),
            ("settings", "Settings"),
        ]
        for page, label in nav_items:
            button = tk.Button(
                self.sidebar,
                text=label,
                command=lambda selected=page: self.show_page(selected),
                relief="flat",
                bd=0,
                padx=18,
                pady=12,
                anchor="w",
                cursor="hand2",
                font=("Segoe UI", 10, "bold"),
            )
            button.pack(fill="x", padx=14, pady=3)
            self.nav_buttons[page] = button

        recent_title = tk.Label(
            self.sidebar,
            text="Recent Searches",
            bg=self.palette["sidebar"],
            fg="#9fb0c8",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        recent_title.pack(fill="x", padx=20, pady=(28, 8))
        self.recent_frame = tk.Frame(self.sidebar, bg=self.palette["sidebar"])
        self.recent_frame.pack(fill="x", padx=14)
        self._refresh_recent_searches()
        self._update_nav_styles()

    def _build_topbar(self) -> None:
        topbar = tk.Frame(self.body, bg=self.palette["bg"], height=86)
        topbar.pack(fill="x", padx=18, pady=(18, 10))
        topbar.pack_propagate(False)

        search_card = tk.Frame(topbar, bg=self.palette["surface"], padx=12, pady=10, highlightthickness=1, highlightbackground=self.palette["grid"])
        search_card.pack(side="left", fill="x", expand=True)

        self.search_entry = ttk.Entry(search_card, textvariable=self.search_var, font=("Segoe UI", 11))
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.search_entry.bind("<Return>", lambda _event: self.search_city())

        tb.Button(search_card, text="Search", bootstyle="primary", command=self.search_city).pack(side="left", padx=(10, 0))
        tb.Button(search_card, text="Current Location", bootstyle="info-outline", command=self.use_current_location).pack(side="left", padx=(8, 0))
        tb.Button(search_card, text="Refresh", bootstyle="secondary-outline", command=self.refresh_weather).pack(side="left", padx=(8, 0))

        right_box = tk.Frame(topbar, bg=self.palette["bg"])
        right_box.pack(side="right", padx=(12, 0))
        self.theme_button = tb.Button(
            right_box,
            text="Dark Mode" if self.theme_mode == "light" else "Light Mode",
            bootstyle="secondary",
            command=self.toggle_theme,
        )
        self.theme_button.pack(anchor="e")
        self.status_label = tk.Label(
            right_box,
            textvariable=self.status_var,
            bg=self.palette["bg"],
            fg=self.palette["muted"],
            font=("Segoe UI", 9),
            anchor="e",
        )
        self.status_label.pack(anchor="e", pady=(8, 0))
        self.progress = ttk.Progressbar(right_box, mode="indeterminate", length=150)

    def _update_nav_styles(self) -> None:
        for page, button in self.nav_buttons.items():
            selected = page == self.current_page
            button.configure(
                bg=self.palette["accent"] if selected else self.palette["sidebar"],
                fg="#ffffff" if selected else "#cbd5e1",
                activebackground=self.palette["accent"],
                activeforeground="#ffffff",
            )

    def _refresh_recent_searches(self) -> None:
        if not hasattr(self, "recent_frame"):
            return
        for child in self.recent_frame.winfo_children():
            child.destroy()
        for item in self.database.recent_searches(8):
            label = f"{item['city']}, {item['country']}" if item.get("country") else item["city"]
            button = tk.Button(
                self.recent_frame,
                text=label,
                command=lambda city=item["city"]: self.load_city(city),
                relief="flat",
                bd=0,
                bg=self.palette["sidebar"],
                fg="#d5deea",
                activebackground="#263348",
                activeforeground="#ffffff",
                padx=8,
                pady=6,
                anchor="w",
                cursor="hand2",
                font=("Segoe UI", 9),
            )
            button.pack(fill="x", pady=1)

    def _load_icon(self, file_name: str, size: int) -> ImageTk.PhotoImage | None:
        cache_key = f"{file_name}:{size}:{self.theme_mode}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        path = ICON_DIR / file_name
        if not path.exists():
            return None
        try:
            image = Image.open(path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
        except Exception:
            return None
        self.image_cache[cache_key] = photo
        return photo

    def _card(self, parent: tk.Widget, padx: int = 16, pady: int = 14) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=self.palette["card"],
            padx=padx,
            pady=pady,
            highlightthickness=1,
            highlightbackground=self.palette["grid"],
        )

    def _label(
        self,
        parent: tk.Widget,
        text: str,
        size: int = 10,
        weight: str = "normal",
        color: str | None = None,
        bg: str | None = None,
        anchor: str = "w",
    ) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            bg=bg or self.palette["card"],
            fg=color or self.palette["text"],
            font=("Segoe UI", size, weight),
            anchor=anchor,
            justify="left",
        )

    def show_page(self, page: str) -> None:
        self.current_page = page
        if hasattr(self, "nav_buttons"):
            self._update_nav_styles()
        if not hasattr(self, "page_host"):
            return
        for child in self.page_host.winfo_children():
            child.destroy()

        if page == "dashboard":
            self.render_dashboard()
        elif page == "charts":
            self.render_charts()
        elif page == "historical":
            self.render_historical()
        elif page == "exports":
            self.render_exports()
        elif page == "settings":
            self.render_settings()

    def _empty_page(self, title: str, message: str) -> None:
        card = self._card(self.page_host, padx=28, pady=24)
        card.pack(fill="both", expand=True)
        self._label(card, title, size=20, weight="bold").pack(anchor="w")
        self._label(card, message, size=11, color=self.palette["muted"]).pack(anchor="w", pady=(10, 0))

    def render_dashboard(self) -> None:
        if self.analytics is None:
            self._empty_page("Weather Dashboard", "Search for a city to load real Open-Meteo weather data.")
            return

        scroll = ScrollableFrame(self.page_host, self.palette["bg"])
        inner = scroll.inner
        self._render_current_weather(inner)
        self._render_metric_grid(inner)
        self._render_daily_forecast(inner)
        self._render_hourly_table(inner)

    def _render_current_weather(self, parent: tk.Widget) -> None:
        assert self.analytics is not None
        current = self.analytics.current_conditions()
        location = self.analytics.bundle.location.display_name
        is_day = bool(current.get("is_day", 1))
        icon = self._load_icon(icon_name_for_weather(current.get("weather_code"), is_day), 116)

        card = self._card(parent, padx=24, pady=22)
        card.pack(fill="x", pady=(0, 16))
        if icon:
            tk.Label(card, image=icon, bg=self.palette["card"]).pack(side="left", padx=(0, 18))

        text_box = tk.Frame(card, bg=self.palette["card"])
        text_box.pack(side="left", fill="both", expand=True)
        self._label(text_box, location, size=18, weight="bold").pack(anchor="w")
        self._label(text_box, current.get("weather_label", "Unavailable"), size=11, color=self.palette["muted"]).pack(anchor="w", pady=(4, 8))
        temperature = current.get("temperature_2m")
        temp_text = "Unavailable" if temperature is None else f"{float(temperature):.1f} C"
        self._label(text_box, temp_text, size=42, weight="bold", color=self.palette["accent"]).pack(anchor="w")

        detail_box = tk.Frame(card, bg=self.palette["card"])
        detail_box.pack(side="right", padx=(18, 0))
        details = [
            ("Feels like", current.get("apparent_temperature"), " C"),
            ("Humidity", current.get("relative_humidity_2m"), "%"),
            ("Wind", current.get("wind_speed_10m"), " km/h"),
            ("Pressure", current.get("pressure_msl"), " hPa"),
        ]
        for label, value, suffix in details:
            text = "Unavailable" if value is None else f"{float(value):.1f}{suffix}"
            self._label(detail_box, f"{label}: {text}", size=10, color=self.palette["muted"]).pack(anchor="e", pady=2)

    def _render_metric_grid(self, parent: tk.Widget) -> None:
        assert self.analytics is not None
        metrics = self.analytics.summary_metrics()
        grid = tk.Frame(parent, bg=self.palette["bg"])
        grid.pack(fill="x", pady=(0, 16))
        for column in range(4):
            grid.columnconfigure(column, weight=1, uniform="metric")
        for index, (label, value) in enumerate(metrics.items()):
            card = self._card(grid, padx=14, pady=12)
            row, column = divmod(index, 4)
            card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
            self._label(card, label, size=9, color=self.palette["muted"]).pack(anchor="w")
            self._label(card, value, size=15, weight="bold").pack(anchor="w", pady=(6, 0))

    def _render_daily_forecast(self, parent: tk.Widget) -> None:
        assert self.analytics is not None
        section = self._card(parent)
        section.pack(fill="x", pady=(0, 16))
        self._label(section, "7-Day Forecast", size=14, weight="bold").pack(anchor="w", pady=(0, 10))

        row = tk.Frame(section, bg=self.palette["card"])
        row.pack(fill="x")
        rows = self.analytics.weekly_forecast_rows()
        for index, item in enumerate(rows):
            row.columnconfigure(index, weight=1, uniform="forecast")
            daily = tk.Frame(row, bg=self.palette["card_alt"], padx=10, pady=10)
            daily.grid(row=0, column=index, sticky="nsew", padx=4)
            icon = self._load_icon(icon_name_for_weather(item["weather_code"], True), 42)
            if icon:
                tk.Label(daily, image=icon, bg=self.palette["card_alt"]).pack()
            self._label(daily, item["date"], size=9, weight="bold", bg=self.palette["card_alt"], anchor="center").pack(fill="x")
            self._label(daily, item["label"], size=8, color=self.palette["muted"], bg=self.palette["card_alt"], anchor="center").pack(fill="x", pady=(3, 4))
            self._label(daily, f"{item['high']} / {item['low']}", size=10, weight="bold", bg=self.palette["card_alt"], anchor="center").pack(fill="x")
            self._label(daily, f"Rain {item['rain']}", size=8, color=self.palette["muted"], bg=self.palette["card_alt"], anchor="center").pack(fill="x", pady=(3, 0))

    def _render_hourly_table(self, parent: tk.Widget) -> None:
        assert self.analytics is not None
        card = self._card(parent)
        card.pack(fill="x", pady=(0, 16))
        self._label(card, "Next 24 Hours", size=14, weight="bold").pack(anchor="w", pady=(0, 10))

        columns = ("time", "temperature", "feels_like", "humidity", "rain", "wind", "condition")
        table = ttk.Treeview(card, columns=columns, show="headings", height=10)
        headings = {
            "time": "Time",
            "temperature": "Temp",
            "feels_like": "Feels",
            "humidity": "Humidity",
            "rain": "Rain",
            "wind": "Wind",
            "condition": "Condition",
        }
        for column, heading in headings.items():
            table.heading(column, text=heading)
            table.column(column, anchor="center", width=120)
        table.column("condition", width=190)
        for row in self.analytics.hourly_rows(24):
            table.insert("", "end", values=tuple(row[column] for column in columns))
        table.pack(fill="x")

    def render_charts(self) -> None:
        if self.analytics is None:
            self._empty_page("Charts", "Search for a city first. Charts are drawn only after real API data is available.")
            return

        toolbar_card = self._card(self.page_host, padx=14, pady=10)
        toolbar_card.pack(fill="x", pady=(0, 12))
        self._label(toolbar_card, "Analytics Dashboard", size=17, weight="bold").pack(side="left")
        tb.Button(toolbar_card, text="Open Interactive Plotly Dashboard", bootstyle="primary", command=self.open_interactive_dashboard).pack(side="right")

        scroll = ScrollableFrame(self.page_host, self.palette["bg"])
        for chart_id, title, builder in ChartFactory(self.analytics, self.theme_mode == "dark").chart_definitions():
            card = self._card(scroll.inner, padx=12, pady=10)
            card.pack(fill="x", pady=(0, 14))
            self._label(card, title, size=12, weight="bold").pack(anchor="w", pady=(0, 6))
            fig = builder()
            canvas = FigureCanvasTkAgg(fig, master=card)
            canvas.draw()
            widget = canvas.get_tk_widget()
            widget.configure(height=330)
            widget.pack(fill="x", expand=True)
            toolbar = NavigationToolbar2Tk(canvas, card, pack_toolbar=False)
            toolbar.update()
            toolbar.pack(anchor="e")

    def render_historical(self) -> None:
        if self.analytics is None:
            self._empty_page("Historical Analytics", "Search for a city first to load historical Open-Meteo archive data.")
            return

        scroll = ScrollableFrame(self.page_host, self.palette["bg"])
        header = self._card(scroll.inner)
        header.pack(fill="x", pady=(0, 14))
        self._label(header, "Historical Weather Analytics", size=18, weight="bold").pack(anchor="w")
        self._label(header, f"Trend: {self.analytics.temperature_trend_label()}", size=12, color=self.palette["muted"]).pack(anchor="w", pady=(8, 0))

        chart_card = self._card(scroll.inner)
        chart_card.pack(fill="x", pady=(0, 14))
        fig = ChartFactory(self.analytics, self.theme_mode == "dark").historical_trend()
        canvas = FigureCanvasTkAgg(fig, master=chart_card)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", expand=True)

        table_card = self._card(scroll.inner)
        table_card.pack(fill="x", pady=(0, 16))
        self._label(table_card, "Historical Daily Records", size=14, weight="bold").pack(anchor="w", pady=(0, 10))
        frame = self.analytics.frames.historical_daily.tail(30)
        columns = [column for column in ["time", "temperature_2m_mean", "temperature_2m_max", "temperature_2m_min", "precipitation_sum", "wind_speed_10m_max"] if column in frame]
        table = ttk.Treeview(table_card, columns=columns, show="headings", height=12)
        for column in columns:
            table.heading(column, text=column.replace("_", " ").title())
            table.column(column, anchor="center", width=150)
        for _, row in frame.iterrows():
            values = []
            for column in columns:
                value = row[column]
                if column == "time":
                    value = value.strftime("%Y-%m-%d")
                elif isinstance(value, (float, int)):
                    value = f"{value:.2f}"
                values.append(value)
            table.insert("", "end", values=values)
        table.pack(fill="x")

    def render_exports(self) -> None:
        if self.analytics is None:
            self._empty_page("Exports", "Load a city first, then export CSV, Excel, PDF, and PNG files.")
            return

        card = self._card(self.page_host, padx=20, pady=18)
        card.pack(fill="x", pady=(0, 14))
        self._label(card, "Export Center", size=18, weight="bold").pack(anchor="w")
        self._label(card, "Files are saved locally in the app exports folder.", size=10, color=self.palette["muted"]).pack(anchor="w", pady=(6, 14))

        actions = tk.Frame(card, bg=self.palette["card"])
        actions.pack(fill="x")
        tb.Button(actions, text="Export CSV", bootstyle="primary-outline", command=self.export_csv).pack(side="left", padx=(0, 8))
        tb.Button(actions, text="Export Excel", bootstyle="success-outline", command=self.export_excel).pack(side="left", padx=8)
        tb.Button(actions, text="Export PDF Report", bootstyle="danger-outline", command=self.export_pdf).pack(side="left", padx=8)
        tb.Button(actions, text="Export PNG Charts", bootstyle="info-outline", command=self.export_png).pack(side="left", padx=8)
        tb.Button(actions, text="Open Exports Folder", bootstyle="secondary", command=self.open_exports_folder).pack(side="right")

        history_card = self._card(self.page_host)
        history_card.pack(fill="both", expand=True)
        self._label(history_card, "Recent Exports", size=14, weight="bold").pack(anchor="w", pady=(0, 10))
        columns = ("type", "city", "path", "created")
        table = ttk.Treeview(history_card, columns=columns, show="headings", height=12)
        for column, heading, width in [
            ("type", "Type", 110),
            ("city", "City", 180),
            ("path", "Path", 560),
            ("created", "Created", 160),
        ]:
            table.heading(column, text=heading)
            table.column(column, width=width, anchor="w")
        for row in self.database.export_history(15):
            table.insert("", "end", values=(row["export_type"], row["city"], row["file_path"], row["created_at"]))
        table.pack(fill="both", expand=True)

    def render_settings(self) -> None:
        card = self._card(self.page_host, padx=22, pady=20)
        card.pack(fill="x", pady=(0, 14))
        self._label(card, "Settings", size=18, weight="bold").pack(anchor="w")

        auto = ttk.Checkbutton(
            card,
            text="Auto-refresh weather data",
            variable=self.auto_refresh_var,
            command=self.save_settings,
        )
        auto.pack(anchor="w", pady=(16, 8))

        row = tk.Frame(card, bg=self.palette["card"])
        row.pack(anchor="w", pady=(0, 10))
        self._label(row, "Refresh interval in minutes", bg=self.palette["card"]).pack(side="left", padx=(0, 10))
        spinbox = ttk.Spinbox(row, from_=5, to=120, increment=5, textvariable=self.refresh_minutes_var, width=8, command=self.save_settings)
        spinbox.pack(side="left")
        tb.Button(row, text="Save", bootstyle="primary-outline", command=self.save_settings).pack(side="left", padx=8)

        tools = tk.Frame(card, bg=self.palette["card"])
        tools.pack(fill="x", pady=(12, 0))
        tb.Button(tools, text="Clear API Cache", bootstyle="warning-outline", command=self.clear_cache).pack(side="left")
        tb.Button(tools, text="Toggle Fullscreen", bootstyle="secondary-outline", command=lambda: self.attributes("-fullscreen", not bool(self.attributes("-fullscreen")))).pack(side="left", padx=8)

    def search_city(self) -> None:
        city = self.search_var.get().strip()
        if not city:
            messagebox.showwarning(APP_NAME, "Please type a city name first.")
            return
        self.load_city(city)

    def load_city(self, city: str) -> None:
        self._run_background(lambda: self.client.fetch_by_city(city), self._set_weather_bundle)

    def refresh_weather(self) -> None:
        if self.bundle is None:
            self.load_city(DEFAULT_CITY)
            return
        location = self.bundle.location
        self._run_background(lambda: self.client.fetch_by_location(location), self._set_weather_bundle)

    def use_current_location(self) -> None:
        def worker() -> WeatherBundle:
            location = detect_current_location_windows()
            return self.client.fetch_by_location(location)

        self._run_background(worker, self._set_weather_bundle)

    def _load_initial_city(self) -> None:
        recent = self.database.recent_searches(1)
        city = recent[0]["city"] if recent else DEFAULT_CITY
        self.search_var.set(city)
        self.load_city(city)

    def _run_background(self, worker, on_success) -> None:
        if self.loading:
            return
        self.loading = True
        self.status_var.set("Loading real Open-Meteo data...")
        self.progress.pack(anchor="e", pady=(6, 0))
        self.progress.start(12)

        def task() -> None:
            try:
                result = worker()
            except Exception as error:
                self.after(0, lambda err=error: self._handle_background_error(err))
                return
            self.after(0, lambda value=result: self._handle_background_success(value, on_success))

        threading.Thread(target=task, daemon=True).start()

    def _handle_background_success(self, result, on_success) -> None:
        self.progress.stop()
        self.progress.pack_forget()
        self.loading = False
        on_success(result)

    def _handle_background_error(self, error: Exception) -> None:
        self.progress.stop()
        self.progress.pack_forget()
        self.loading = False
        message = str(error) if isinstance(error, WeatherApiError) else f"Unexpected error: {error}"
        self.status_var.set("Could not load weather data")
        messagebox.showerror(APP_NAME, message)

    def _set_weather_bundle(self, bundle: WeatherBundle) -> None:
        self.bundle = bundle
        self.analytics = WeatherAnalytics(bundle)
        self.search_var.set(bundle.location.display_name)
        fallback = (
            bundle.forecast.get("_weathervision_cached_fallback")
            or bundle.historical.get("_weathervision_cached_fallback")
            or bundle.air_quality.get("_weathervision_cached_fallback")
        )
        suffix = " (cached offline data)" if fallback else ""
        self.status_var.set(f"Updated {datetime.now().strftime('%H:%M')}{suffix}")
        self._refresh_recent_searches()
        self.show_page(self.current_page)
        self._schedule_auto_refresh()

    def _schedule_auto_refresh(self) -> None:
        if self.auto_refresh_job:
            self.after_cancel(self.auto_refresh_job)
            self.auto_refresh_job = None
        if not self.auto_refresh_var.get() or self.bundle is None:
            return
        minutes = max(int(self.refresh_minutes_var.get()), 5)
        self.auto_refresh_job = self.after(minutes * 60 * 1000, self._auto_refresh)

    def _auto_refresh(self) -> None:
        if self.bundle is not None and not self.loading:
            self.refresh_weather()

    def toggle_theme(self) -> None:
        self.theme_mode = "dark" if self.theme_mode == "light" else "light"
        self.palette = PALETTES[self.theme_mode]
        self.database.set_setting("theme_mode", self.theme_mode)
        self.style.theme_use(DARK_THEME if self.theme_mode == "dark" else LIGHT_THEME)
        self.image_cache.clear()
        self._build_shell()

    def save_settings(self) -> None:
        minutes = max(int(self.refresh_minutes_var.get()), 5)
        self.refresh_minutes_var.set(minutes)
        self.database.set_setting("auto_refresh_enabled", bool(self.auto_refresh_var.get()))
        self.database.set_setting("refresh_minutes", minutes)
        self.status_var.set("Settings saved")
        self._schedule_auto_refresh()

    def clear_cache(self) -> None:
        removed = self.database.clear_cache()
        self.status_var.set(f"Cleared {removed} cached API responses")
        messagebox.showinfo(APP_NAME, f"Cleared {removed} cached API responses.")

    def export_csv(self) -> None:
        if self.analytics is None:
            return
        paths = self.exporter.export_csv_bundle(self.analytics)
        self.status_var.set(f"Exported {len(paths)} CSV files")
        messagebox.showinfo(APP_NAME, f"Exported {len(paths)} CSV files.")
        self.render_exports()

    def export_excel(self) -> None:
        if self.analytics is None:
            return
        try:
            path = self.exporter.export_excel(self.analytics)
        except ImportError as error:
            messagebox.showerror(APP_NAME, f"Excel export needs openpyxl. Install requirements.txt.\n\n{error}")
            return
        self.status_var.set(f"Excel exported: {path.name}")
        messagebox.showinfo(APP_NAME, f"Excel exported:\n{path}")
        self.render_exports()

    def export_pdf(self) -> None:
        if self.analytics is None:
            return
        path = self.exporter.export_pdf_report(self.analytics, self.theme_mode == "dark")
        self.status_var.set(f"PDF exported: {path.name}")
        messagebox.showinfo(APP_NAME, f"PDF exported:\n{path}")
        self.render_exports()

    def export_png(self) -> None:
        if self.analytics is None:
            return
        paths = self.exporter.export_chart_snapshots(self.analytics, self.theme_mode == "dark")
        self.status_var.set(f"Exported {len(paths)} chart images")
        messagebox.showinfo(APP_NAME, f"Exported {len(paths)} chart images.")
        self.render_exports()

    def open_interactive_dashboard(self) -> None:
        if self.analytics is None:
            return
        try:
            path = EXPORT_DIR / f"interactive_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            build_plotly_dashboard(self.analytics, path)
            webbrowser.open(path.resolve().as_uri())
            self.database.log_export("Plotly HTML", str(path), self.analytics.bundle.location.display_name)
            self.status_var.set(f"Interactive dashboard created: {path.name}")
        except Exception as error:
            messagebox.showerror(APP_NAME, str(error))

    def open_exports_folder(self) -> None:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(EXPORT_DIR)
        else:
            webbrowser.open(EXPORT_DIR.resolve().as_uri())
