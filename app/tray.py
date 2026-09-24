"""Windows system-tray icon for the windowless build.

``run.exe`` is built with ``console=False``, so before this module existed the
only way to stop it was Task Manager. The tray icon gives the front-desk
operator an obvious handle on the process: what it is, whether it is healthy,
where the logs are, whether it starts with Windows, and how to quit it.

The icon is drawn at runtime with Pillow rather than shipped as a .ico, so the
single-file build needs no bundled asset.

Everything here degrades gracefully. A machine with no interactive desktop
(a scheduled task running as SYSTEM, or an NSSM service) cannot show a tray
icon at all - in that case :func:`run_with_tray` reports failure and the caller
serves in the foreground exactly as before.
"""

import logging
import os
import sys
import threading
import webbrowser

from app import autostart

logger = logging.getLogger("itsthe1.api")

# Tray colours: unmistakable at 16x16.
_GREEN = (34, 160, 74)
_RED = (200, 44, 44)
_GREY = (120, 120, 120)


def _make_image(colour):
    """A filled circle on a transparent square, drawn at 64x64."""
    from PIL import Image, ImageDraw

    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, size - 4, size - 4), fill=colour)
    return image


def _health_colour():
    """Green when every check passes, red when one fails, grey if unknown."""
    try:
        from app.monitoring.routes import build_health
        return _GREEN if build_health(deep=True)["healthy"] else _RED
    except Exception:
        return _GREY


def run_with_tray(server, host, port, log_dir):
    """Serve in a background thread and show a tray icon on this thread.

    ``server`` is a waitress server created with ``create_server`` - it exposes
    ``run()`` and ``close()``, which is what lets Quit shut down cleanly rather
    than killing the process mid-request.

    Returns True if the tray ran (and has now exited), False if a tray could not
    be created, leaving the caller to serve in the foreground instead.
    """
    try:
        import pystray
    except ImportError:
        logger.warning(
            "pystray is not installed; running without a tray icon. "
            "Install it with: pip install pystray"
        )
        return False

    status_url = f"http://127.0.0.1:{port}/status"

    serve_thread = threading.Thread(target=server.run, name="waitress", daemon=True)
    serve_thread.start()
    logger.info("Server thread started; building tray icon")

    def on_status(icon, item):
        webbrowser.open(status_url)

    def on_logs(icon, item):
        try:
            os.startfile(log_dir)  # noqa: S606 - Windows shell open, path is ours
        except Exception as exc:
            logger.warning("Could not open the log folder %s: %s", log_dir, exc)

    def on_refresh(icon, item):
        icon.icon = _make_image(_health_colour())

    def on_toggle_autostart(icon, item):
        try:
            autostart.set_enabled(not autostart.is_enabled())
        except Exception:
            logger.warning("Could not change the autostart setting", exc_info=True)
        # Redraw so the tick matches what actually happened, including a failure.
        icon.update_menu()

    def on_quit(icon, item):
        logger.info("Quit selected from the tray icon - shutting down")
        try:
            server.close()
        except Exception:
            logger.warning("Error while closing the server", exc_info=True)
        icon.visible = False
        icon.stop()

    from app.version import APP_NAME, __version__

    items = [
        pystray.MenuItem(f"{APP_NAME} v{__version__}", None, enabled=False),
        pystray.MenuItem(f"Listening on {host}:{port}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open status page", on_status, default=True),
        pystray.MenuItem("Open log folder", on_logs),
        pystray.MenuItem("Refresh health", on_refresh),
    ]

    # The tick is read from the registry each time the menu opens, so it stays
    # honest even if the entry is changed from outside this process.
    if autostart.is_supported():
        items.append(pystray.MenuItem(
            "Start with Windows",
            on_toggle_autostart,
            checked=lambda item: autostart.is_enabled(),
        ))

    items += [
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    ]

    menu = pystray.Menu(*items)

    icon = pystray.Icon(
        "itsthe1api",
        icon=_make_image(_GREY),
        title=f"{APP_NAME} v{__version__} - {host}:{port}",
        menu=menu,
    )

    def on_ready(icon):
        icon.visible = True
        # Colour the icon once the first health check has run, then keep it
        # current. Daemon thread so it never delays Quit.
        def poll():
            import time
            while icon.visible:
                try:
                    icon.icon = _make_image(_health_colour())
                except Exception:
                    pass
                time.sleep(30)

        threading.Thread(target=poll, name="tray-health", daemon=True).start()

    try:
        icon.run(setup=on_ready)
    except Exception:
        # No interactive desktop (SYSTEM service, session 0). Not fatal.
        logger.warning(
            "Could not create the tray icon - serving without one. This is normal "
            "when running as a Windows service.", exc_info=True
        )
        return False

    logger.info("Tray icon closed; process exiting")
    return True
