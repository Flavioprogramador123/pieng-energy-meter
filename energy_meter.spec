# -*- mode: python ; coding: utf-8 -*-
# Build: .venv\Scripts\pyinstaller.exe energy_meter.spec
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = (
    collect_submodules("pymodbus")
    + collect_submodules("minimalmodbus")
    + collect_submodules("tinytuya")
    + collect_submodules("apscheduler")
    + collect_submodules("uvicorn")
    + [
        "psycopg2",
        "serial",
        "serial.tools.list_ports",
    ]
)

a = Analysis(
    ["run_server.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("app/static", "app/static"),
        ("app/templates", "app/templates"),
        ("home/static", "home/static"),
        ("home/templates", "home/templates"),
        ("home/device_catalog.json", "home"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["firebase_admin", "googleapiclient", "google.oauth2"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EnergyMeterServer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="EnergyMeterServer",
)
