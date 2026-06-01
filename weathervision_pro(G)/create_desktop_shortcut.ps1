param(
    [string]$ExePath = (Join-Path $PSScriptRoot "dist\WeatherVision Pro.exe")
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ExePath)) {
    throw "EXE not found at '$ExePath'. Build the app with PyInstaller first."
}

$resolvedExe = (Resolve-Path $ExePath).Path
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "WeatherVision Pro.lnk"
$iconPath = Join-Path $PSScriptRoot "assets\icons\weather_icon.ico"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $resolvedExe
$shortcut.WorkingDirectory = Split-Path $resolvedExe
$shortcut.IconLocation = $iconPath
$shortcut.Description = "WeatherVision Pro desktop weather analytics"
$shortcut.Save()

Write-Host "Created desktop shortcut: $shortcutPath"
