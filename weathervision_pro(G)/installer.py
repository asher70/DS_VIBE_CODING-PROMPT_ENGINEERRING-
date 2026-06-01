"""Small Windows installer for WeatherVision Pro.

This installer is intentionally separate from the main app. It copies the
already-built WeatherVision Pro EXE into the user's LocalAppData Programs
folder and creates normal Windows shortcuts.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk


APP_NAME = "WeatherVision Pro"
APP_EXE_NAME = "WeatherVision Pro.exe"


def bundled_root() -> Path:
    """Return the folder PyInstaller uses for bundled installer files."""

    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def source_exe_path() -> Path:
    """Find the app EXE either inside the setup bundle or in local dist."""

    bundled = bundled_root() / APP_EXE_NAME
    if bundled.exists():
        return bundled
    local = Path(__file__).resolve().parent / "dist" / APP_EXE_NAME
    return local


def install_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(local_app_data) / "Programs" / APP_NAME


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def create_shortcut(shortcut_path: Path, target_path: Path) -> None:
    """Create a real `.lnk` shortcut using Windows Script Host through PowerShell."""

    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    script = f"""
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut({ps_quote(str(shortcut_path))})
$shortcut.TargetPath = {ps_quote(str(target_path))}
$shortcut.WorkingDirectory = {ps_quote(str(target_path.parent))}
$shortcut.IconLocation = {ps_quote(str(target_path))}
$shortcut.Description = 'WeatherVision Pro desktop weather analytics'
$shortcut.Save()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=True,
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def install_application() -> Path:
    """Copy the app and create Windows shortcuts."""

    source = source_exe_path()
    if not source.exists():
        raise FileNotFoundError(f"Could not find {APP_EXE_NAME}. Build the app EXE first.")

    destination_dir = install_dir()
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_exe = destination_dir / APP_EXE_NAME
    shutil.copy2(source, destination_exe)

    desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    start_menu = (
        Path(os.environ.get("APPDATA", str(Path.home())))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / APP_NAME
    )
    create_shortcut(desktop / f"{APP_NAME}.lnk", destination_exe)
    create_shortcut(start_menu / f"{APP_NAME}.lnk", destination_exe)
    return destination_exe


class InstallerWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} Setup")
        self.geometry("520x280")
        self.resizable(False, False)
        self.configure(bg="#0d1117")
        self._center()

        frame = tk.Frame(self, bg="#111827", padx=28, pady=24)
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(
            frame,
            text=f"Install {APP_NAME}",
            bg="#111827",
            fg="#f8fafc",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            frame,
            text="This setup installs the local desktop app and creates Windows shortcuts.",
            bg="#111827",
            fg="#aeb8c7",
            font=("Segoe UI", 10),
            wraplength=430,
            justify="left",
        ).pack(anchor="w", pady=(8, 18))

        self.status = tk.StringVar(value=f"Install location: {install_dir()}")
        tk.Label(
            frame,
            textvariable=self.status,
            bg="#111827",
            fg="#cbd5e1",
            font=("Segoe UI", 9),
            wraplength=430,
            justify="left",
        ).pack(anchor="w", pady=(0, 14))

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 16))

        buttons = tk.Frame(frame, bg="#111827")
        buttons.pack(fill="x")
        self.install_button = ttk.Button(buttons, text="Install", command=self.start_install)
        self.install_button.pack(side="right")
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=(0, 8))

    def _center(self) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 520) // 2
        y = (self.winfo_screenheight() - 280) // 2
        self.geometry(f"520x280+{x}+{y}")

    def start_install(self) -> None:
        self.install_button.configure(state="disabled")
        self.progress.start(12)
        self.status.set("Installing...")

        def worker() -> None:
            try:
                installed_exe = install_application()
            except Exception as error:
                self.after(0, lambda err=error: self.install_failed(err))
                return
            self.after(0, lambda path=installed_exe: self.install_finished(path))

        threading.Thread(target=worker, daemon=True).start()

    def install_finished(self, path: Path) -> None:
        self.progress.stop()
        self.status.set(f"Installed successfully: {path}")
        messagebox.showinfo(APP_NAME, f"{APP_NAME} installed successfully.")
        self.destroy()

    def install_failed(self, error: Exception) -> None:
        self.progress.stop()
        self.install_button.configure(state="normal")
        self.status.set("Installation failed.")
        messagebox.showerror(APP_NAME, str(error))


def main() -> None:
    app = InstallerWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
