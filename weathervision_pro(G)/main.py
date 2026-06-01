"""Application entry point for WeatherVision Pro."""

from __future__ import annotations

import argparse
import ctypes
import sys

from config import APP_ID, ensure_app_folders
from ui import WeatherVisionApp, show_splash_screen


def configure_windows_process() -> None:
    """Set Windows taskbar identity and high-DPI behavior."""

    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="WeatherVision Pro desktop application")
    parser.add_argument("--no-splash", action="store_true", help="Start without the splash screen")
    args = parser.parse_args()

    ensure_app_folders()
    configure_windows_process()

    # Create the main window first (hidden) so there is only ONE Tk instance.
    # ttkbootstrap stores a singleton Style that holds a reference to the Tk
    # master; if a second Tk() were created (e.g. for the splash) and then
    # destroyed before ttkbootstrap initialises, it crashes on Python 3.14+.
    app = WeatherVisionApp()
    app.withdraw()  # hide while the splash is shown

    if not args.no_splash:
        show_splash_screen(app)  # Toplevel child, no second Tk()

    app.deiconify()  # reveal the main window
    app.mainloop()


if __name__ == "__main__":
    main()
