"""File + console logging for the API.

The shipped executable is built with ``console=False``, so nothing that the app
prints is ever visible. Every message therefore also goes to a rotating log file
under ``LOG_DIR`` (``logs/api.log`` by default, next to run.exe).

Two log files are written:
  * ``api.log``    - everything at LOG_LEVEL and above
  * ``errors.log`` - WARNING and above only, so problems are easy to spot
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.config import Config
from app.version import APP_NAME, __version__

_LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Guard so repeated create_app() calls (tests, reloader) do not stack handlers.
_configured = False


def configure_logging():
    """Attach rotating file handlers to the root logger. Idempotent."""
    global _configured
    if _configured:
        return logging.getLogger("itsthe1.api")

    level = getattr(logging, str(Config.LOG_LEVEL).upper(), logging.INFO)
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    root = logging.getLogger()
    root.setLevel(level)

    try:
        os.makedirs(Config.LOG_DIR, exist_ok=True)

        app_handler = RotatingFileHandler(
            os.path.join(Config.LOG_DIR, "api.log"),
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        app_handler.setLevel(level)
        app_handler.setFormatter(formatter)
        root.addHandler(app_handler)

        error_handler = RotatingFileHandler(
            os.path.join(Config.LOG_DIR, "errors.log"),
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(formatter)
        root.addHandler(error_handler)
    except Exception as exc:
        # A read-only install folder must not stop the API from serving.
        print(f"[WARNING] File logging disabled: {exc}")

    # Console output too, but only when there is a console to write to.
    if sys.stdout is not None:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level)
        console.setFormatter(formatter)
        root.addHandler(console)

    # Waitress logs every bind/error under this name; keep it visible.
    logging.getLogger("waitress").setLevel(logging.INFO)

    _configured = True
    return logging.getLogger("itsthe1.api")


def log_startup_banner(logger, host, port):
    """Write an unmistakable block to the log when the server comes up."""
    logger.info("=" * 78)
    logger.info("%s v%s starting", APP_NAME, __version__)
    logger.info("Listening on   : http://%s:%s", host, port)
    logger.info("Health check   : http://127.0.0.1:%s/health", port)
    logger.info("Status page    : http://127.0.0.1:%s/status", port)
    logger.info("Config file    : %s", Config.CONFIG_FILE or "NOT FOUND")
    logger.info("Database       : %s", Config.safe_database_uri())
    logger.info("Schema         : %s", Config.SCHEMA_NAME)
    logger.info("Storage path   : %s", Config.BaseDirectoryPath)
    logger.info("Log directory  : %s", Config.LOG_DIR)
    if Config.CONFIG_ERROR:
        logger.warning("CONFIG PROBLEM : %s", Config.CONFIG_ERROR)
    logger.info("=" * 78)
