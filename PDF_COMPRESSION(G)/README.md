# Local PDF Compressor

This is a local Windows desktop app for compressing PDF files.

It uses the existing PyMuPDF/Pillow compression engine as the backend logic.
The desktop UI is only a wrapper around that engine.

## Architecture

The app is split into three simple layers:

1. `pdf_compressor_app/ui`
   - Shows the desktop window.
   - Handles drag-and-drop, file picker, dropdowns, buttons, progress, and messages.

2. `pdf_compressor_app/application`
   - Checks that the selected PDF and save location are valid.
   - Converts technical errors into user-friendly messages.

3. `pdf_compressor_app/engine`
   - Contains the actual PDF compression code.
   - This is where the existing PyMuPDF/Pillow compression logic lives.

The UI does not compress PDFs directly. It asks the application layer to do the work, and the application layer calls the engine.

## Why PySide6

PySide6 is used because it is a real desktop GUI framework for Windows, supports drag-and-drop directly, and has clean background-thread support.

## Threading

PDF compression can take time. If it ran on the same thread as the window, the app would look frozen.

This app keeps the window on the main UI thread and runs compression in a background `QThread`.
The worker sends progress messages back to the UI thread.

## Run From Source

```powershell
py -3.13 -m venv .venv313
.\.venv313\Scripts\activate
python -m pip install -r requirements.txt
python -m pdf_compressor_app.main
```

## Build Windows Executable

The packaging tool is PyInstaller. It collects Python, the app files, and required packages into one local Windows app folder.

```powershell
.\package_app.ps1
```

After the build finishes, open:

```text
dist\PDFCompressor\PDFCompressor.exe
```
