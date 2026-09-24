"""Start the API automatically when the operator logs in.

Windows autostart lives in the per-user Run key::

    HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run

which needs no admin rights and, unlike a Windows service, runs inside the
interactive desktop session - which is what the tray icon needs to exist at all.

``config.json`` holds the switch (``"StartWithWindows": true``) and the registry
entry mirrors it, so the tray toggle and a hand-edited config never disagree.
:func:`sync` applies the setting on every start, which also repairs the entry
after the exe is rebuilt, renamed or moved to another folder.

Nothing here is fatal. On a non-Windows machine, or when the registry refuses
the write, the functions report failure and the API serves exactly as before.
"""

import logging
import os
import sys

from app.config import Config, save_setting
from app.version import APP_NAME

logger = logging.getLogger("itsthe1.api")

# Where Windows looks for per-user logon commands.
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

# Our entry in that key. Keep it stable: changing it orphans existing entries.
VALUE_NAME = APP_NAME

# The config.json key holding the setting.
SETTING_NAME = "StartWithWindows"


def is_supported():
    """True when this machine has a Windows registry to write to."""
    return sys.platform == "win32"


def launch_command():
    """The command line Windows should run at logon, quoted for the registry."""
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}"'

    # Running from source. pythonw.exe keeps a console window from flashing up
    # at logon; not every environment ships it, so fall back to python.exe.
    launcher = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(launcher):
        launcher = sys.executable

    # Always the project's entry point, never sys.argv[0]: a helper script that
    # imports this module must not end up as the thing Windows launches.
    script = os.path.join(Config.BASE_DIR, "run.py")

    return f'"{launcher}" "{script}"'


def current_command():
    """What the Run key launches for us today, or None when there is no entry."""
    if not is_supported():
        return None

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            command, _value_type = winreg.QueryValueEx(key, VALUE_NAME)
            return command
    except FileNotFoundError:
        return None
    except OSError:
        logger.warning("Could not read the autostart entry", exc_info=True)
        return None


def is_enabled():
    """True when Windows is currently set to start this API at logon."""
    return current_command() is not None


def _write_entry():
    import winreg

    command = launch_command()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command)
    return command


def _remove_entry():
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        pass  # Already gone, which is what was asked for.


def set_enabled(enabled):
    """Turn autostart on or off and remember the choice in config.json.

    Raises OSError if the registry write fails - the caller decides how loudly
    to complain. A config.json that cannot be written is only logged: the
    registry is already correct, so autostart behaves as asked; the setting just
    will not survive the next restart.
    """
    enabled = bool(enabled)

    if not is_supported():
        raise RuntimeError("Autostart is only available on Windows")

    if enabled:
        logger.info("Autostart enabled: %s", _write_entry())
    else:
        _remove_entry()
        logger.info("Autostart disabled")

    Config.START_WITH_WINDOWS = enabled

    try:
        path = save_setting(SETTING_NAME, enabled)
    except Exception as exc:
        logger.warning("Autostart is now %s, but %s could not be saved to config.json: %s",
                       "on" if enabled else "off", SETTING_NAME, exc)
    else:
        logger.info("Saved %s = %s to %s", SETTING_NAME, enabled, path)

    return enabled


def sync():
    """Make the registry entry match the setting. Call once at startup.

    Returns the state now in effect, or None when autostart is unavailable.
    """
    if not is_supported():
        return None

    desired = bool(Config.START_WITH_WINDOWS)
    existing = current_command()

    try:
        if desired:
            wanted = launch_command()
            if existing != wanted:
                _write_entry()
                logger.info("Autostart entry %s: %s",
                            "updated" if existing else "created", wanted)
        elif existing is not None:
            _remove_entry()
            logger.info("Autostart entry removed (%s is off)", SETTING_NAME)
    except OSError:
        logger.warning("Could not update the autostart entry", exc_info=True)
        return None

    return desired
