"""Efficient, incrementally-readable whole-table GETs.

Every ``GET /<table>`` in this API used to answer with the entire table:

    Log.query.all()   ->  99,722 ORM objects  ->  27 MB of JSON

A client that re-reads every table after a write therefore pulls ~109 MB
before it can see that a room went vacant. That is the whole reason a 141 ms
``POST /checkout`` took over a minute to show up on screen - the write was
never the slow part, the re-sync afterwards was.

This module fixes both halves of it:

* **Reads go through SQLAlchemy Core.** No ORM instances are built for rows
  that are about to be turned straight into dicts. Measured 1.6-2.5x faster on
  the big tables, at a fraction of the memory.
* **Every dump accepts incremental parameters.** A client that remembers where
  it got to last time asks for the handful of rows that are new instead of the
  whole table - ``GET /log?since_id=99722`` is 1 row, not 99,722.

The dict each service builds is untouched, so an unparameterised request
returns byte-for-byte what it always did. Nothing existing has to change to
keep working; a client only opts in to the fast path when it is ready.

Parameters, all optional and all valid on every dump endpoint:

    since_id=<int>     rows whose sequence column is strictly greater
    since=<iso8601>    rows added at or after this time (tables with AddedAt)
    limit=<int>        at most this many rows
    offset=<int>       skip this many rows (needs a stable order, so one is
                       applied for you)
    order=asc|desc     by sequence column; default asc, and only applied when
                       it is asked for or when limit/offset needs it

An unparsable value is a 400 rather than a silently ignored parameter, because
a client that thinks it is reading incrementally and is really reading the
whole table has no way to notice on its own.
"""

from datetime import datetime

from flask import abort, request
from sqlalchemy import select
from werkzeug.exceptions import HTTPException

from app import db

# A limit above this is treated as "no limit". Stops a typo like limit=1e9
# turning into an OFFSET/FETCH plan that is slower than the plain scan it
# replaced.
_LIMIT_CEILING = 1_000_000


def _int_arg(name):
    """Parse an integer query argument, or 400 if it is not one."""
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        abort(400, description=f"{name} must be a whole number, got {raw!r}")


def _datetime_arg(name):
    """Parse an ISO-8601 query argument, or 400 if it is not one."""
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    # Accept a trailing Z, which fromisoformat only learned in 3.11 and which
    # every JavaScript client sends by default.
    cleaned = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        abort(400, description=f"{name} must be an ISO-8601 date-time, got {raw!r}")


_TRUE = {"1", "true", "yes", "y", "t"}
_FALSE = {"0", "false", "no", "n", "f"}


def _coerce(name, column, value):
    """Turn a query string into something the column's type will compare against.

    A ``bit`` column compared against the string ``"1"`` relies on SQL Server's
    implicit conversion, and an ``int`` column against ``"41"`` on the same.
    Both happen to work and neither should be depended on, so the value is
    converted here where a bad one can still be reported as a 400.
    """
    python_type = None
    try:
        python_type = column.type.python_type
    except NotImplementedError:  # a type with no Python equivalent
        return value

    if python_type is bool:
        lowered = value.strip().lower()
        if lowered in _TRUE:
            return True
        if lowered in _FALSE:
            return False
        abort(400, description=f"{name} must be true or false, got {value!r}")

    if python_type is int:
        try:
            return int(value)
        except ValueError:
            abort(400, description=f"{name} must be a whole number, got {value!r}")

    if python_type is float:
        try:
            return float(value)
        except ValueError:
            abort(400, description=f"{name} must be a number, got {value!r}")

    return value


def fetch_rows(model, build, sequence_column="Id", filters=None):
    """Read ``model``'s table through Core and map each row with ``build``.

    ``build`` is handed a SQLAlchemy ``Row``, which supports the same
    ``row.ColumnName`` access an ORM instance does - so a service switching to
    this keeps its dict literal exactly as it was.

    ``sequence_column`` is the monotonically increasing column that ``since_id``
    and ``order`` work on. It is ``Id`` for every table but ``guestversion``,
    whose primary key is composite.

    ``filters`` maps a query-argument name to a column, for the equality
    filters that make sense on that table - ``{"checkin_id": Log.CheckinId}``
    turns ``?checkin_id=41`` into ``WHERE CheckinId = 41``.

    Database errors are returned as ``{"error": "..."}`` rather than raised,
    which is what these endpoints have always done and what the partner
    documentation and Postman assertions expect.
    """
    table = model.__table__

    try:
        sequence = table.c[sequence_column]
    except KeyError:  # a caller naming a column that does not exist
        raise ValueError(
            f"{model.__name__} has no column {sequence_column!r} to sequence on"
        )

    try:
        statement = select(table)

        since_id = _int_arg("since_id")
        if since_id is not None:
            statement = statement.where(sequence > since_id)

        since = _datetime_arg("since")
        if since is not None:
            if "AddedAt" not in table.c:
                abort(400, description=(
                    f"{table.name} has no AddedAt column, so ?since= cannot be "
                    f"answered for it. Use ?since_id= instead."
                ))
            statement = statement.where(table.c.AddedAt >= since)

        for argument, column in (filters or {}).items():
            value = request.args.get(argument)
            if value is not None and value != "":
                statement = statement.where(column == _coerce(argument, column, value))

        limit = _int_arg("limit")
        offset = _int_arg("offset")
        if limit is not None and limit < 1:
            abort(400, description=f"limit must be 1 or more, got {limit}")
        if offset is not None and offset < 0:
            abort(400, description=f"offset must be 0 or more, got {offset}")
        if limit is not None and limit >= _LIMIT_CEILING:
            limit = None

        order = request.args.get("order", "").lower()
        if order not in ("", "asc", "desc"):
            abort(400, description=f"order must be asc or desc, got {order!r}")

        # SQL Server renders limit/offset as OFFSET ... FETCH NEXT, which is a
        # syntax error without an ORDER BY. So a page always gets an order even
        # when the caller did not ask for one - and a plain unparameterised
        # dump still gets none, keeping it exactly as cheap as it was.
        if order == "desc":
            statement = statement.order_by(sequence.desc())
        elif order == "asc" or limit is not None or offset is not None:
            statement = statement.order_by(sequence.asc())

        if offset is not None:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)

        rows = db.session.execute(statement).all()
        return [build(row) for row in rows]

    except HTTPException:
        # A 400 raised by abort() above - a bad request we deliberately chose
        # to report as one. Never dressed up as a database failure.
        raise
    except Exception as exc:
        db.session.rollback()
        return {"error": str(exc)}
