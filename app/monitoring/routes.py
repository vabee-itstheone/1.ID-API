"""Monitoring endpoints and the request instrumentation that feeds them."""

import logging
import os
import platform
import socket
import time
import traceback

from flask import Blueprint, Response, current_app, g, jsonify, request
from sqlalchemy import text
from werkzeug.exceptions import HTTPException

from app.config import Config
from app.monitoring.dashboard import DASHBOARD_HTML
from app.monitoring.metrics import metrics
from app.version import APP_NAME, __version__, build_info

logger = logging.getLogger("itsthe1.api.monitoring")

monitoring_bp = Blueprint("monitoring", __name__)

# Monitoring traffic is excluded from both the log file and the counters. A
# browser parked on /status polls every 5 seconds; without this the dashboard
# would show nothing but itself and the "requests served" figure would be
# meaningless as a measure of real API usage.
_QUIET_PATHS = {"/", "/ping", "/health", "/metrics", "/metrics/reset",
                "/status", "/routes", "/version", "/favicon.ico"}

# Real API traffic, but far too much of it to write a line for. /changes exists
# to be polled - once a second is a reasonable client, and that is 3,600 log
# lines an hour of "nothing happened". So it is counted like any other request
# and appears on the dashboard, but a successful one is logged at DEBUG. A
# failure still gets its WARNING, which is the part an operator needs.
_QUIET_LOG_PATHS = {"/changes"}


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #

# A browser on /status polls /health every 5 seconds. When the database is down
# that would write the same multi-line ODBC error to the log 720 times an hour
# and bury everything else, so identical failures are logged at most once per
# _HEALTH_LOG_INTERVAL seconds with a count of what was suppressed.
_HEALTH_LOG_INTERVAL = 300
_last_db_log = {"signature": None, "at": 0.0, "suppressed": 0}


def _log_db_failure(exc):
    signature = str(exc)[:200]
    now = time.monotonic()

    same_error = signature == _last_db_log["signature"]
    within_window = (now - _last_db_log["at"]) < _HEALTH_LOG_INTERVAL

    if same_error and within_window:
        _last_db_log["suppressed"] += 1
        return

    if _last_db_log["suppressed"]:
        logger.error(
            "Database health check still failing (%d identical failures suppressed "
            "in the last %d seconds)", _last_db_log["suppressed"], _HEALTH_LOG_INTERVAL
        )
    logger.error("Database health check failed: %s", exc)
    _last_db_log.update({"signature": signature, "at": now, "suppressed": 0})


def check_database():
    """Run 'SELECT 1' against the configured database.

    Returns a dict with ok/latencyMs/error - never raises.
    """
    from app import db

    started = time.perf_counter()
    try:
        db.session.execute(text("SELECT 1"))
        db.session.commit()
        if _last_db_log["signature"] is not None:
            logger.info("Database connection recovered")
            _last_db_log.update({"signature": None, "at": 0.0, "suppressed": 0})
        return {
            "ok": True,
            "latencyMs": round((time.perf_counter() - started) * 1000, 1),
            "uri": Config.safe_database_uri(),
            "schema": Config.SCHEMA_NAME,
            "error": None,
        }
    except Exception as exc:
        db.session.rollback()
        _log_db_failure(exc)
        return {
            "ok": False,
            "latencyMs": round((time.perf_counter() - started) * 1000, 1),
            "uri": Config.safe_database_uri(),
            "schema": Config.SCHEMA_NAME,
            "error": str(exc)[:1000],
        }


def check_storage():
    """Confirm the attachment/image directory exists and is writable.

    A missing directory is created rather than merely reported: on a fresh
    install nobody has made it yet, and the API cannot store guest documents
    without it. Only a genuine failure to create it is reported as unhealthy.
    """
    path = Config.BaseDirectoryPath
    try:
        if not os.path.isdir(path):
            try:
                os.makedirs(path, exist_ok=True)
                logger.info("Created missing storage directory: %s", path)
            except Exception as exc:
                return {
                    "ok": False,
                    "path": path,
                    "error": f"Directory does not exist and could not be created: {exc}",
                }
        probe = os.path.join(path, ".write_probe.tmp")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return {"ok": True, "path": path, "error": None}
    except Exception as exc:
        return {"ok": False, "path": path, "error": str(exc)[:500]}


def check_config():
    """Report whether config.json was actually found and parsed.

    A file that loaded only because of the backslash repair in config.py is
    reported ok - the settings are live - but carries a warning, so it shows on
    the dashboard without making the instance look dead.
    """
    return {
        "ok": Config.CONFIG_ERROR is None,
        "file": Config.CONFIG_FILE,
        "error": Config.CONFIG_ERROR,
        "warning": getattr(Config, "CONFIG_WARNING", None),
    }


def build_health(deep=True):
    """Assemble the full health document. ``deep=False`` skips I/O checks."""
    checks = {"config": check_config()}
    if deep:
        checks["database"] = check_database()
        checks["storage"] = check_storage()

    healthy = all(check["ok"] for check in checks.values())

    return {
        "status": "healthy" if healthy else "unhealthy",
        "healthy": healthy,
        **build_info(),
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "port": Config.PORT,
        "uptimeSeconds": round(metrics.uptime_seconds(), 1),
        "uptimeHuman": metrics.snapshot()["uptimeHuman"],
        "totalRequests": metrics.total_requests,
        "totalErrors": metrics.total_errors,
        "checks": checks,
        "logDirectory": Config.LOG_DIR,
    }


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@monitoring_bp.route("/ping", methods=["GET"])
def ping():
    """Cheapest possible liveness probe - no database, no disk."""
    return Response("pong", mimetype="text/plain")


@monitoring_bp.route("/version", methods=["GET"])
def version():
    return jsonify(build_info())


@monitoring_bp.route("/health", methods=["GET"])
def health():
    """Full readiness check. 200 when healthy, 503 when something is broken.

    Pass ``?deep=false`` to skip the database and disk probes.
    """
    deep = request.args.get("deep", "true").lower() not in ("false", "0", "no")
    payload = build_health(deep=deep)
    return jsonify(payload), (200 if payload["healthy"] else 503)


@monitoring_bp.route("/metrics", methods=["GET"])
def metrics_endpoint():
    return jsonify(metrics.snapshot())


@monitoring_bp.route("/metrics/reset", methods=["POST"])
def metrics_reset():
    metrics.reset()
    logger.info("Metrics counters reset via /metrics/reset")
    return jsonify({"reset": True})


@monitoring_bp.route("/routes", methods=["GET"])
def routes():
    """Every URL this build serves - the fastest way to confirm a deployment."""
    listing = []
    for rule in current_app.url_map.iter_rules():
        methods = sorted(rule.methods - {"HEAD", "OPTIONS"})
        if not methods:
            continue
        listing.append({
            "rule": str(rule),
            "methods": methods,
            "endpoint": rule.endpoint,
            "blueprint": rule.endpoint.split(".")[0] if "." in rule.endpoint else None,
        })
    listing.sort(key=lambda item: item["rule"])
    return jsonify({"count": len(listing), "routes": listing})


@monitoring_bp.route("/status", methods=["GET"])
def status_page():
    """Human-facing dashboard. Open this in a browser to see the API is alive."""
    html = DASHBOARD_HTML.replace("{{APP_NAME}}", APP_NAME).replace("{{VERSION}}", __version__)
    return Response(html, mimetype="text/html")


@monitoring_bp.route("/favicon.ico", methods=["GET"])
def favicon():
    """Browsers always ask for this; answer quietly instead of logging a 404."""
    return Response(status=204)


@monitoring_bp.route("/", methods=["GET"])
def index():
    """Root gives a one-line orientation instead of a 404."""
    return jsonify({
        "name": APP_NAME,
        "version": __version__,
        "status": "running",
        "dashboard": "/status",
        "health": "/health",
        "routes": "/routes",
    })


# --------------------------------------------------------------------------- #
# Instrumentation
# --------------------------------------------------------------------------- #

def _soft_error(response):
    """Detect a failure that was returned with a 2xx status code.

    The lookup services (/country, /room, ...) catch their exceptions and return
    ``{"error": "..."}`` with HTTP 200, and the business endpoints return
    ``{"hasErrors": true}``. Both look like success to anything watching status
    codes. We do not change those response bodies - the WPF client depends on
    them - but we do surface them on the dashboard and in the log.

    Returns the error text, or None.
    """
    if response.status_code >= 400 or not response.is_json:
        return None
    try:
        payload = response.get_json(silent=True)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None

    if payload.get("error"):
        return str(payload["error"])
    if payload.get("hasErrors"):
        messages = payload.get("errorMessages") or {}
        if isinstance(messages, dict) and messages:
            return "; ".join(f"{k}: {v}" for k, v in messages.items())
        return "hasErrors=true"
    return None


def init_monitoring(app):
    """Register the monitoring blueprint, request hooks and JSON error pages."""

    app.register_blueprint(monitoring_bp)

    @app.before_request
    def _start_timer():
        g._monitor_start = time.perf_counter()

    @app.after_request
    def _record(response):
        if request.path in _QUIET_PATHS:
            return response

        started = getattr(g, "_monitor_start", None)
        duration_ms = (time.perf_counter() - started) * 1000 if started else 0.0

        soft_error = _soft_error(response)
        metrics.record_request(
            request.method, request.path, response.status_code, duration_ms, error=soft_error
        )

        if response.status_code >= 400 or soft_error:
            log = logger.warning
        elif request.path in _QUIET_LOG_PATHS:
            log = logger.debug
        else:
            log = logger.info
        log(
            "%s %s -> %s (%.0f ms) from %s%s",
            request.method,
            request.full_path.rstrip("?"),
            response.status_code,
            duration_ms,
            request.remote_addr,
            f" | {soft_error}" if soft_error else "",
        )
        return response

    @app.errorhandler(HTTPException)
    def _handle_http_exception(exc):
        """404/405/400 as JSON - this is an API, HTML error pages help nobody."""
        return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": exc.description},
            "status": exc.code,
            "path": request.path,
            "method": request.method,
        }), exc.code

    @app.errorhandler(Exception)
    def _handle_unexpected(exc):
        """Last line of defence: log the traceback, return JSON, stay up."""
        started = getattr(g, "_monitor_start", None)
        duration_ms = (time.perf_counter() - started) * 1000 if started else 0.0

        logger.error(
            "Unhandled exception on %s %s: %s\n%s",
            request.method,
            request.path,
            exc,
            traceback.format_exc(),
        )
        metrics.record_request(request.method, request.path, 500, duration_ms, error=exc)

        return jsonify({
            "hasErrors": True,
            "errorMessages": {"general": "Internal server error"},
            "detail": str(exc)[:500],
            "status": 500,
            "path": request.path,
            "method": request.method,
        }), 500

    logger.info("Monitoring enabled: /ping /health /metrics /routes /status")
    return app
