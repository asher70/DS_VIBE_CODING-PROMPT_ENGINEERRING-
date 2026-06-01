# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules


# Keep hidden imports focused. Collecting every Plotly submodule can pull in
# large unrelated packages from a developer machine and make builds very slow.
hiddenimports = collect_submodules("ttkbootstrap") + [
    "PIL._tkinter_finder",
    "openpyxl",
    "plotly.graph_objects",
    "plotly.subplots",
    "plotly.io._html",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("assets", "assets")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch",
        "tensorflow",
        "sklearn",
        "scipy",
        "pyarrow",
        "imageio",
        "imageio_ffmpeg",
        "sympy",
        "numba",
        "llvmlite",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="WeatherVision Pro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icons/weather_icon.ico",
)
