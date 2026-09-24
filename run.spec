# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
# Production build: windowless (no console window).
#   pyinstaller run.spec --noconfirm
# Produces dist/run.exe. Copy config.json next to the exe before starting it.
#
# For a build that shows a console window (useful when diagnosing a server that
# refuses to start) use run_console.spec instead.


a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    # certifi's cacert.pem. Without it every outbound HTTPS call dies with
    # "Could not find a suitable TLS CA certificate bundle". Named here
    # rather than left to the automatic hook so a build cannot lose it.
    datas=collect_data_files('certifi'),
    hiddenimports=[
        'pyodbc', 'PIL', 'PIL.Image', 'PIL.ImageDraw',
        'googletrans', 'tzlocal', 'requests', 'certifi',
        'sqlalchemy', 'sqlalchemy.orm', 'flask_sqlalchemy', 'waitress',
        # Monitoring package - imported dynamically inside create_app().
        'app.monitoring', 'app.monitoring.routes', 'app.monitoring.metrics',
        'app.monitoring.dashboard', 'app.logging_setup', 'app.version',
        # System tray icon. pystray picks its backend at import time, so the
        # Windows one has to be named explicitly or the frozen build cannot
        # find it and falls back to running with no tray icon.
        'app.tray', 'pystray', 'pystray._win32',
        # "Start with Windows": imported inside main(), and winreg inside the
        # functions that touch the Run key.
        'app.autostart', 'winreg',
        # Change feed and the shared table reader, both imported inside
        # create_app() the same way the monitoring package is.
        'app.changes', 'app.changes.routes', 'app.changes.services',
        'app.utilities.table_query', 'app.utilities.http_response',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='run',
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
)
