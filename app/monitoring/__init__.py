"""Health, metrics and live status dashboard for the API.

Nothing in here touches business logic. It exists so that an operator looking at
a running instance can answer three questions without reading code:

  1. Is the process alive?            -> GET /ping
  2. Can it reach the database?       -> GET /health
  3. What has it been doing?          -> GET /status  (HTML dashboard)

Wire it up from ``create_app()`` with ``init_monitoring(app)``.
"""

from app.monitoring.metrics import Metrics, metrics
from app.monitoring.routes import monitoring_bp, init_monitoring

__all__ = ["Metrics", "metrics", "monitoring_bp", "init_monitoring"]
