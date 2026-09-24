"""In-memory request counters.

Waitress serves requests on a thread pool, so every mutation is guarded by a
lock. Everything lives in memory and resets when the process restarts - that is
deliberate: this is a "is it healthy right now" panel, not a metrics database.
"""

import threading
from collections import Counter, deque
from datetime import datetime, timezone

from app.config import Config


def _utcnow():
    return datetime.now(timezone.utc)


class Metrics:
    def __init__(self, history_size=None):
        self._lock = threading.Lock()
        size = history_size or Config.REQUEST_HISTORY_SIZE
        self.started_at = _utcnow()
        self.total_requests = 0
        self.total_errors = 0            # 5xx responses + unhandled exceptions
        self.total_client_errors = 0     # 4xx responses
        self.per_endpoint = Counter()    # "POST /checkin" -> count
        self.status_codes = Counter()    # 200 -> count
        self.last_request_at = None
        self.last_error_at = None
        self.recent_requests = deque(maxlen=size)
        self.recent_errors = deque(maxlen=size)

    def record_request(self, method, path, status_code, duration_ms, error=None):
        key = f"{method} {path}"
        now = _utcnow()
        entry = {
            "time": now.isoformat(),
            "method": method,
            "path": path,
            "status": status_code,
            "durationMs": round(duration_ms, 1),
        }
        if error:
            entry["error"] = str(error)[:500]

        with self._lock:
            self.total_requests += 1
            self.per_endpoint[key] += 1
            self.status_codes[status_code] += 1
            self.last_request_at = now
            self.recent_requests.appendleft(entry)

            if status_code >= 500 or error:
                self.total_errors += 1
                self.last_error_at = now
                self.recent_errors.appendleft(entry)
            elif status_code >= 400:
                self.total_client_errors += 1

    def uptime_seconds(self):
        return (_utcnow() - self.started_at).total_seconds()

    def snapshot(self):
        """Thread-safe copy of everything, ready to jsonify."""
        with self._lock:
            return {
                "startedAt": self.started_at.isoformat(),
                "uptimeSeconds": round(self.uptime_seconds(), 1),
                "uptimeHuman": format_duration(self.uptime_seconds()),
                "totalRequests": self.total_requests,
                "totalErrors": self.total_errors,
                "totalClientErrors": self.total_client_errors,
                "lastRequestAt": self.last_request_at.isoformat() if self.last_request_at else None,
                "lastErrorAt": self.last_error_at.isoformat() if self.last_error_at else None,
                "statusCodes": dict(sorted(self.status_codes.items())),
                "topEndpoints": [
                    {"endpoint": name, "count": count}
                    for name, count in self.per_endpoint.most_common(15)
                ],
                "recentRequests": list(self.recent_requests),
                "recentErrors": list(self.recent_errors),
            }

    def reset(self):
        with self._lock:
            self.total_requests = 0
            self.total_errors = 0
            self.total_client_errors = 0
            self.per_endpoint.clear()
            self.status_codes.clear()
            self.last_request_at = None
            self.last_error_at = None
            self.recent_requests.clear()
            self.recent_errors.clear()


def format_duration(seconds):
    """900 -> '15m 0s', 90061 -> '1d 1h 1m'."""
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


# Module-level singleton shared by the request hooks and the dashboard.
metrics = Metrics()
