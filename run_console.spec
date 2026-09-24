# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
# Diagnostic build: identical to run.spec but keeps a console window open so
# startup errors are visible immediately.
#   pyinstaller run_console.spec --noconfirm
# Produces dist/run_console.exe alongside the normal dist/run.exe.


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
        'app.monitoring', 'app.monitoring.routes', 'app.monitoring.metrics',
        'app.monitoring.dashboard', 'app.logging_setup', 'app.version',
        'app.tray', 'pystray', 'pystray._win32',
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
    name='run_console',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
