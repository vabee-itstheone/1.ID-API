"""The cheap "has anything happened?" question.

A front-desk client wants one thing after a check-out: to know, immediately,
that room 101 is now vacant. Until this endpoint existed the only way to find
out was to re-read every table - 109 MB - and the answer arrived over a minute
late.

``revision()`` answers the same question in a single round trip that touches
only indexes and the 59-row room table, so a client can ask several times a
second without costing anything. The tables it fingerprints are the ones a
business write always touches.

Two properties matter more than speed:

* **It is derived from the database, not from this process.** A check-out
  written by the desktop application straight to SQL Server moves the revision
  exactly as one written through ``POST /checkout`` does, and a restart of the
  API does not reset it. An in-process counter would have been cheaper and
  wrong on both counts.
* **It notices updates, not just inserts.** ``MAX(Id)`` alone would miss the
  part of a check-out that matters most - ``room.IsChecked`` flipping to 0 is
  an UPDATE, and so is ``checkin.IsActive``. The room table therefore
  contributes a checksum over exactly the columns that describe occupancy, and
  every business write also inserts a ``log`` row, which covers the rest.
"""

from sqlalchemy import text

from app import db

# Sequence probes. Each is a ``MAX(Id)`` over a table whose rows are only ever
# appended, which SQL Server answers from the primary-key index without
# reading the table. Order matters only in that it must stay stable, because
# the revision token is built from it positionally.
_SEQUENCE_TABLES = (
    ("checkin", "Id"),
    ("checkout", "Id"),
    ("checkinguest", "Id"),
    ("roomchange", "Id"),
    ("mainguestchange", "Id"),
    ("guest", "Id"),
    ("log", "Id"),
)

# Short prefixes keep the revision token readable in a log line and in a URL.
_TOKEN_PREFIX = {
    "checkin": "ci",
    "checkout": "co",
    "checkinguest": "cg",
    "roomchange": "rc",
    "mainguestchange": "mg",
    "guest": "gu",
    "log": "lg",
}


def _schema(app_config):
    """The bracketed schema the models are mapped to, e.g. ``[db].[itsthe1.id]``."""
    return app_config["SCHEMA_NAME"]


def _revision_sql(schema):
    """One SELECT that fingerprints every table a business write touches.

    Built as a single statement on purpose: seven separate round trips to a
    SQL Server on another machine would cost more than the query does.
    """
    sequences = ",\n           ".join(
        f"(SELECT MAX({column}) FROM {schema}.[{table}]) AS seq_{table}"
        for table, column in _SEQUENCE_TABLES
    )
    return text(
        f"SELECT {sequences},\n"
        f"           (SELECT CHECKSUM_AGG(BINARY_CHECKSUM(Id, IsChecked, "
        f"ISNULL(CheckinId, -1))) FROM {schema}.[room]) AS room_state,\n"
        f"           (SELECT COUNT(*) FROM {schema}.[room] WHERE IsChecked = 1) "
        f"AS occupied"
    )


def revision(app_config):
    """Return ``(token, detail)`` describing the current state of the database.

    ``token`` is an opaque string a client hands back as ``?since=``; it
    changes whenever anything a front desk cares about changes. ``detail``
    breaks it down per table so a client can fetch just the rows it is missing
    with ``?since_id=``.
    """
    row = db.session.execute(_revision_sql(_schema(app_config))).one()
    mapping = row._mapping

    tables = {
        table: mapping[f"seq_{table}"] or 0
        for table, _column in _SEQUENCE_TABLES
    }
    room_state = mapping["room_state"] or 0
    occupied = mapping["occupied"] or 0

    token = ".".join(
        [f"{_TOKEN_PREFIX[table]}{tables[table]}" for table, _c in _SEQUENCE_TABLES]
        + [f"rm{room_state}"]
    )

    return token, {
        "maxIds": tables,
        "roomState": room_state,
        "occupiedRooms": occupied,
    }


def _parse_token(token):
    """Split a revision token back into ``{name: value}``, or None if it is not one.

    Strict on purpose. A token from a different build of this API - one part
    longer, one part shorter, a prefix this version does not know - must be
    reported as unusable, not quietly reconciled against what happens to
    overlap. Getting that wrong is the worst bug this endpoint could have: the
    client would be told nothing had changed and would stop refreshing.
    """
    inverse = {prefix: table for table, prefix in _TOKEN_PREFIX.items()}
    inverse["rm"] = "room"

    parts = {}
    for piece in token.split("."):
        prefix, value = piece[:2], piece[2:]
        name = inverse.get(prefix)
        if name is None or value == "" or name in parts:
            return None
        parts[name] = value

    if set(parts) != set(inverse.values()):
        return None
    return parts


def changed_tables(previous_token, current_token):
    """Which named parts of the revision moved between two tokens.

    Returns ``None`` when ``previous_token`` is missing or is not a token this
    build produced, which a caller should read as "you have no usable baseline,
    do a full read".
    """
    if not previous_token:
        return None

    before = _parse_token(previous_token)
    after = _parse_token(current_token)
    if before is None or after is None:
        return None

    return sorted(name for name, value in after.items() if before[name] != value)
