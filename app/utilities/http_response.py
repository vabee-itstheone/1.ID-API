"""Two transport savings that need no change from the client.

The table endpoints answer with a lot of JSON - 27 MB for ``GET /log`` on a
year-old hotel database. Two things can be done about that without any client
knowing:

**gzip.** This JSON is extremely repetitive, so it compresses about 5.6x. Every
HTTP client in this system already advertises ``Accept-Encoding: gzip`` and
decompresses transparently, so the saving is free to collect. Compression level
1 is deliberate: on 27 MB it costs 164 ms and saves 22 MB, where level 6 costs
303 ms to save a further 0.6 MB. For a client on hotel Wi-Fi the fast level
wins outright on time to first render, which is the number being reduced here.

**Conditional GET.** Every sizeable response gets an ``ETag``. A client that
sends the tag back as ``If-None-Match`` gets a 304 with no body when nothing
has changed - and after a check-out most tables have not, so ``guest``,
``guestattachment``, ``payment`` and ``roomchange`` cost it nothing. That saves
the client its JSON parse as well as the transfer, which is where most of the
delay actually was. The database read still happens on the server, so a client
that wants to skip that too should ask ``/changes`` first.

Both are skipped below ``_MIN_BODY_BYTES``, where the CPU and the extra round
trip cost more than they save.
"""

import gzip
import hashlib

from flask import request

# Below this a response fits in a packet or two; compressing and hashing it is
# a pointless expense.
_MIN_BODY_BYTES = 4096

# See the module docstring: fast beats small for a LAN client.
_COMPRESS_LEVEL = 1

_COMPRESSIBLE_TYPES = {
    "application/json",
    "text/html",
    "text/plain",
    "text/css",
    "application/javascript",
}


def _is_compressible(response):
    content_type = (response.content_type or "").split(";")[0].strip().lower()
    return content_type in _COMPRESSIBLE_TYPES


def init_http_response(app):
    """Install the ETag and gzip hooks on ``app``.

    Registered from ``create_app()`` after every blueprint, so it sees every
    response the API produces.
    """

    @app.after_request
    def _tag_and_compress(response):
        # Streamed and already-encoded responses are left alone: touching
        # either means buffering something the sender chose not to buffer.
        if response.direct_passthrough or response.headers.get("Content-Encoding"):
            return response
        if response.status_code != 200 or not _is_compressible(response):
            return response

        try:
            body = response.get_data()
        except RuntimeError:
            return response

        if len(body) < _MIN_BODY_BYTES:
            return response

        # Weak, because gzip means the bytes on the wire are not the bytes
        # hashed. blake2b costs 32 ms on 27 MB - noise next to what one 304
        # saves the client.
        response.set_etag(hashlib.blake2b(body, digest_size=16).hexdigest(), weak=True)
        response.headers.setdefault("Vary", "Accept-Encoding")

        # Turns the response into a 304 with an empty body when the caller's
        # If-None-Match matches. It also honours Range, which can turn this
        # into a 206 or a 416 - in either case the body no longer matches the
        # Content-Range and Content-Length that were just computed for it, so
        # anything other than a plain 200 is handed back uncompressed.
        response = response.make_conditional(request)
        if response.status_code != 200:
            return response

        if "gzip" not in (request.headers.get("Accept-Encoding") or "").lower():
            return response

        compressed = gzip.compress(body, _COMPRESS_LEVEL)
        # Only worth sending if it actually came out smaller - an
        # already-compressed payload, such as a JPEG in a JSON field, can grow.
        if len(compressed) >= len(body):
            return response

        response.set_data(compressed)
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Content-Length"] = str(len(compressed))
        return response
