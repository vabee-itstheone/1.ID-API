"""Entry point for the ITSthe1.ID API.

Run from source:      python run.py
Run the built exe:    dist\\run.exe

The windowless build shows a **system tray icon** - right-click it to open the
status page or the log folder, to turn "Start with Windows" on or off, or to
quit. Use --no-tray to serve in the foreground instead (what a Windows service
or scheduled task should do).

Once it is up, open http://127.0.0.1:<PORT>/status in a browser to confirm it
is working. Everything printed here is also written to logs/api.log, which is
the only visible output when running the windowless build.
"""

import logging
import os
import socket
import sys

# Ensure working directory is where the script/exe is located.
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(os.path.abspath(sys.executable)))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config
from app.logging_setup import configure_logging, log_startup_banner

app = create_app()


def _port_owner_exists(host, port):
    """True when something is already listening on this host/port.

    Windows lets a second process bind a port that is already bound: a stale
    instance does NOT produce "address already in use". Both processes end up
    listening, the older one quietly wins every connection, and the new build
    looks like it started fine while serving nothing.

    Binding a probe socket does not detect this - a bind on 127.0.0.1 does not
    conflict with an existing wildcard (0.0.0.0) bind, even with
    SO_EXCLUSIVEADDRUSE. So ask the only question that has an unambiguous
    answer: can we open a connection to it? If something accepts, the port is
    already being served.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.settimeout(1.0)
    try:
        return probe.connect_ex((host, port)) == 0
    except OSError:
        return False
    finally:
        probe.close()


def main():
    logger = configure_logging()
    host = Config.HOST
    port = int(Config.PORT)
    use_tray = "--no-tray" not in sys.argv

    log_startup_banner(logger, host, port)

    if Config.CONFIG_ERROR:
        # The settings never loaded, so the API is about to serve an empty
        # SQLite database. Say so in the strongest terms available to us.
        logger.critical("CONFIG NOT LOADED - the API is running on defaults, "
                        "NOT on your settings: %s", Config.CONFIG_ERROR)

    probe_host = "127.0.0.1" if host == "0.0.0.0" else host
    if _port_owner_exists(probe_host, port):
        logger.critical("Port %s is already in use on %s - refusing to start.",
                        port, probe_host)
        logger.critical(
            "Another instance of this API is almost certainly already running. "
            "Quit it from its tray icon, or find it with: "
            "netstat -ano | findstr :%s", port
        )
        sys.exit(1)

    try:
        from waitress import create_server
    except ImportError:
        # Not a fatal problem while developing - fall back so the developer can
        # still exercise the endpoints - but make very clear it is not the
        # production server.
        logger.warning(
            "waitress is not installed; falling back to the Flask development "
            "server. Install it with: pip install waitress"
        )
        app.run(host=host, port=port, debug=False, use_reloader=False)
        return

    try:
        server = create_server(app, host=host, port=port, threads=8)
    except OSError as exc:
        # Almost always "port already in use" - the single most common reason
        # the API looks dead after a restart.
        logger.critical("Could not bind to %s:%s - %s", host, port, exc)
        logger.critical(
            "Another process is probably already using port %s. "
            "Check with: netstat -ano | findstr :%s", port, port
        )
        sys.exit(1)

    if use_tray:
        # Only the interactive build registers a logon command. --no-tray means a
        # service or scheduled task, which Windows already starts on its own.
        from app.autostart import sync as sync_autostart
        state = sync_autostart()
        if state is not None:
            logger.info("Start with Windows: %s", "on" if state else "off")

    try:
        if use_tray:
            from app.tray import run_with_tray
            if run_with_tray(server, host, port, Config.LOG_DIR):
                return
            # Tray unavailable (no desktop session) - carry on in the foreground.
            logger.info("Continuing without a tray icon")
        server.run()
    except KeyboardInterrupt:
        logger.info("Interrupted - shutting down")
        server.close()
    except Exception:
        logging.getLogger("itsthe1.api").critical("Server stopped unexpectedly", exc_info=True)
        raise


if __name__ == "__main__":
    main()
