"""Single source of truth for the API version.

Bump ``__version__`` whenever you cut a new build. The value is reported by
``GET /version``, ``GET /health`` and the ``/status`` dashboard, so the person
looking at a running instance can tell exactly which build is live.
"""

import os
import sys
from datetime import datetime, timezone

# Semantic version of this API. Bump before every build.
__version__ = "1.0.1"

# Human readable name shown on the status dashboard.
APP_NAME = "ITSthe1.ID API"

# Filled in at import time so the dashboard can show when the process started.
STARTED_AT = datetime.now(timezone.utc)


def build_info():
    """Return a dict describing this build/runtime. Safe to jsonify."""
    return {
        "name": APP_NAME,
        "version": __version__,
        "frozen": bool(getattr(sys, "frozen", False)),
        "python": sys.version.split()[0],
        "pid": os.getpid(),
        "startedAt": STARTED_AT.isoformat(),
    }
