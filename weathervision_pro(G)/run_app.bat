@echo off
echo ============================================
echo  WeatherVision Pro - Starting...
echo ============================================
cd /d "%~dp0"
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Application failed to start.
    echo Please make sure Python is installed and requirements are met.
    pause
)
