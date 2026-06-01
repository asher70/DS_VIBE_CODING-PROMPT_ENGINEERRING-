# WeatherVision Pro

WeatherVision Pro is a local Windows desktop weather analytics app built with Python, Tkinter, ttkbootstrap, pandas, Matplotlib, Plotly, SQLite, and Open-Meteo.

The app uses real Open-Meteo API responses only. It does not generate fake temperatures, humidity, wind, rain, air quality, or chart values.

## Features

- Search weather by city
- Current weather dashboard
- 7-day forecast
- Hourly forecast table
- Historical weather analytics
- 15 real-data charts
- Interactive Plotly HTML dashboard with zoom and hover tooltips
- Recent searches saved locally
- Auto-refresh
- Local SQLite database
- API response caching for faster loading and graceful offline use
- Dark and light themes
- Windows current-location support through Windows Location Services
- Weather condition icons
- PDF weather report export
- Excel export
- CSV export
- PNG chart snapshot export
- Custom app icon
- PyInstaller EXE build
- Desktop shortcut script
- Inno Setup installer script

## Data Sources

All weather data comes from Open-Meteo:

- Geocoding API: converts a city name into latitude and longitude
- Forecast API: current weather, hourly forecast, daily forecast
- Historical Weather API: past weather trends
- Air Quality API: AQI and pollutant data

The Air Quality API is also an Open-Meteo API. It is used because the normal Forecast API does not provide AQI values.

## Folder Structure

```text
weathervision_pro/
├── main.py
├── weather_api.py
├── ui.py
├── charts.py
├── analytics.py
├── database.py
├── export.py
├── config.py
├── assets/
│   ├── icons/
│   ├── images/
│   ├── themes/
│   └── splash/
├── cache/
├── exports/
├── database/
├── requirements.txt
└── README.md
```

Additional packaging files are included:

- `WeatherVisionPro.spec`
- `WeatherVisionPro.iss`
- `create_desktop_shortcut.ps1`
- `installer.py`

## Setup

Open PowerShell in the `weathervision_pro` folder.

Create a virtual environment:

```powershell
py -3.13 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the app:

```powershell
python main.py
```

Run without the splash screen:

```powershell
python main.py --no-splash
```

## How It Works

1. You type a city name.
2. `weather_api.py` asks Open-Meteo Geocoding for latitude and longitude.
3. The app uses those coordinates to call Open-Meteo Forecast, Historical Weather, and Air Quality APIs.
4. `database.py` saves recent searches, settings, export history, and cached API JSON in SQLite.
5. `analytics.py` converts the JSON into pandas tables.
6. `charts.py` draws Matplotlib charts inside the desktop app and Plotly charts in a local HTML dashboard.
7. `export.py` writes CSV, Excel, PDF, and PNG files into the local `exports` folder.

## Current Location

The Current Location button uses Windows Location Services. It does not use third-party IP lookup.

If it fails:

1. Open Windows Settings.
2. Go to Privacy & security.
3. Open Location.
4. Turn on Location services.
5. Try the button again.

## Offline Behavior

The app needs internet for fresh weather data. If internet is unavailable but the same request was cached earlier, it can show the last real Open-Meteo response from SQLite.

The app never fills missing data with random or demo values.

## Charts Included

1. Hourly Temperature Line Chart
2. Weekly Temperature Trend
3. Humidity Area Chart
4. Wind Speed Line Graph
5. Rain Probability Bar Chart
6. UV Index Chart
7. Pressure Trend Chart
8. Sunrise/Sunset Comparison
9. Temperature Heatmap
10. Precipitation Forecast Chart
11. Air Quality Graph
12. Visibility Trend Chart
13. Multi-Day Forecast Comparison
14. Feels Like vs Actual Temperature
15. Historical Weather Trend Graph

## Export Options

Use the Exports page to create:

- CSV files
- Excel workbook
- PDF weather report
- PNG chart snapshots
- Interactive Plotly HTML dashboard

Exports are saved in:

```text
weathervision_pro/exports/
```

When packaged as an installed app, writable app data is saved under:

```text
%LOCALAPPDATA%\WeatherVision Pro\
```

## Build a Windows EXE

From the `weathervision_pro` folder, activate the virtual environment and run:

```powershell
pyinstaller --noconfirm --onefile --windowed --name "WeatherVision Pro" --icon assets\icons\weather_icon.ico --add-data "assets;assets" main.py
```

Or use the included spec file:

```powershell
pyinstaller --noconfirm WeatherVisionPro.spec
```

The EXE will be created at:

```text
dist/WeatherVision Pro.exe
```

## Create a Desktop Shortcut

After building the EXE, run:

```powershell
.\create_desktop_shortcut.ps1
```

This creates:

```text
Desktop/WeatherVision Pro.lnk
```

The shortcut uses:

```text
assets/icons/weather_icon.ico
```

## Build an Installer

### Option 1: Build the included PyInstaller setup EXE

This option does not require Inno Setup. It creates a setup app that installs
`WeatherVision Pro.exe` into:

```text
%LOCALAPPDATA%\Programs\WeatherVision Pro\
```

Build the main app EXE first, then run:

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "WeatherVisionProSetup" --icon assets\icons\weather_icon.ico --add-binary "dist\WeatherVision Pro.exe;." installer.py
```

The installer will be created at:

```text
dist/WeatherVisionProSetup.exe
```

When run, it copies the app EXE and creates Desktop and Start Menu shortcuts.

### Option 2: Build a professional Inno Setup installer

The project includes an Inno Setup script:

```text
WeatherVisionPro.iss
```

Steps:

1. Install Inno Setup from `https://jrsoftware.org/isinfo.php`.
2. Build the PyInstaller EXE first.
3. Open `WeatherVisionPro.iss` in Inno Setup Compiler.
4. Click Compile.
5. The installer will be created in:

```text
installer/WeatherVisionProSetup.exe
```

The installer can create Start Menu and Desktop shortcuts.

## Screenshots

Add screenshots here after running the app:

- Dashboard
- Charts page
- Historical analytics page
- Export center
- Dark mode

## Notes for Beginners

- `main.py` starts the program.
- `ui.py` builds everything you see on screen.
- `weather_api.py` downloads real weather data.
- `analytics.py` turns raw API data into clean tables.
- `charts.py` turns those tables into charts.
- `database.py` stores local app memory using SQLite.
- `export.py` creates files you can share.
- `config.py` stores settings and paths used by the whole app.
