$ErrorActionPreference = "Stop"

$Python = ".\.venv313\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    py -3.13 -m venv .venv313
}

& $Python -m pip install -r requirements.txt
& $Python -m PyInstaller PDFCompressor.spec --clean --noconfirm

Write-Host ""
Write-Host "Build complete:"
Write-Host "dist\PDFCompressor\PDFCompressor.exe"
