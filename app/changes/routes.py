"""``GET /changes`` - the endpoint a client polls instead of re-reading tables.

Two ways to use it:

    GET /changes?since=<token>
        Answers in a couple of milliseconds. Poll it as often as you like.

    GET /changes?since=<token>&wait=25
        Does not answer until something changes, or until ``wait`` seconds have
        passed. A check-out therefore reaches the client within about a quarter
        of a second of the commit, with one idle connection instead of a busy
        poll loop.

Both return the same body, so a client can start with the first form and move
to the second without changing how it reads the response.
"""

import threading
import time

from flask import current_app, jsonify, request

from app import db
from app.changes import changes_bp
from app.changes.services import changed_tables, revision

# How long a waiting request sleeps between probes. A quarter second is below
# the threshold where a front-desk operator would call the update "delayed",
# and at ~2 ms a probe it costs the database nothing worth measuring.
_PROBE_INTERVAL = 0.25

# Waitress serves this app on 8 threads. Long-polls park a thread for their
# whole duration, so they get a hard share of the pool and no more - if every
# permit is taken, a request answers immediately rather than queueing behind
# another client's wait and starving ordinary traffic.
_MAX_WAITERS = 3
_waiters = threading.BoundedSemaphore(_MAX_WAITERS)

# Cap on ?wait=. Long enough to be worth holding a connection for, short
# enough that a client notices a dead server on its own.
_MAX_WAIT_SECONDS = 55


def _wait_seconds():
    """Parse ``?wait=``, clamped to something a thread can safely be parked for."""
    raw = request.args.get("wait")
    if raw is None or raw == "":
        return 0.0
    try:
        wait = float(raw)
    except ValueError:
        return 0.0
    return max(0.0, min(wait, _MAX_WAIT_SECONDS))


def _snapshot():
    """Current revision, with the session released so nothing holds a snapshot.

    A long-poll probes in a loop. Without the rollback, SQL Server would keep
    the read transaction open for the whole wait, which under the default
    isolation level is a lock a writer can end up behind - the endpoint meant
    to make check-outs faster would be delaying them.
    """
    try:
        return revision(current_app.config)
    finally:
        db.session.rollback()


@changes_bp.route('/changes', methods=['GET'])
def changes():
    since = request.args.get("since") or None
    wait = _wait_seconds()

    try:
        token, detail = _snapshot()
    except Exception as exc:
        # Same contract as the table endpoints: a database problem is reported
        # in the body rather than as a 500, so a client's sync loop can log it
        # and carry on polling.
        return jsonify({"error": str(exc)}), 200

    waited = 0.0
    if wait and since and since == token:
        acquired = _waiters.acquire(blocking=False)
        if acquired:
            try:
                deadline = time.monotonic() + wait
                while time.monotonic() < deadline:
                    time.sleep(min(_PROBE_INTERVAL, max(0.0, deadline - time.monotonic())))
                    try:
                        token, detail = _snapshot()
                    except Exception as exc:
                        return jsonify({"error": str(exc)}), 200
                    if token != since:
                        break
                waited = wait - max(0.0, deadline - time.monotonic())
            finally:
                _waiters.release()

    changed = changed_tables(since, token)

    return jsonify({
        "revision": token,
        # None means "no usable baseline" - the client had no ?since=, or one
        # from a different build. Either way it should read in full once.
        "changed": None if changed is None else bool(changed),
        "changedTables": changed,
        "since": since,
        "waitedSeconds": round(waited, 2),
        **detail,
    })
