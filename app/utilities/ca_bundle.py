r"""Give ``requests`` a CA bundle whose path stays valid for the whole run.

A one-file PyInstaller build unpacks itself into ``%TEMP%\_MEIxxxxxx`` and
resolves ``certifi.where()`` to a file inside it. The bundle is written there
at startup, but the folder is ordinary temp: antivirus quarantines files in it,
disk-cleanup tools empty it, and some sites clear %TEMP% on a schedule. This
API is a long-running service, so it is still holding that path hours or days
later, by which point the file can be gone:

    Could not find a suitable TLS CA certificate bundle, invalid path:
    C:\Users\user\AppData\Local\Temp\_MEI212242\certifi\cacert.pem

Every outbound HTTPS call then fails, for what looks like no reason - the exe
was not touched and nothing was reconfigured.

So at startup, while the unpacked copy is still there, take our own copy next
to the exe and point requests at that instead. It is somewhere nothing else
sweeps, and it is refreshed on each start so it cannot go stale.

Running from source needs none of this: site-packages is not temporary.
"""

import logging
import os
import shutil
import sys

logger = logging.getLogger("itsthe1.api")


def _writable_copy(source):
    """Copy the bundle somewhere durable and return the path, or None."""
    from app.config import Config

    # Beside the exe first - that is the operator's own folder, next to
    # config.json. LOG_DIR is the fallback because the app already needs to be
    # able to write there, so it works when the exe sits in Program Files.
    candidates = [
        os.path.join(Config.BASE_DIR, "certs"),
        Config.LOG_DIR,
    ]

    for directory in candidates:
        target = os.path.join(directory, "cacert.pem")
        try:
            os.makedirs(directory, exist_ok=True)
            shutil.copyfile(source, target)
            return target
        except OSError as exc:
            logger.debug("Could not place the CA bundle in %s (%s)", directory, exc)

    logger.warning(
        "Could not copy the CA bundle anywhere durable; falling back to %s, "
        "which may be removed while the service is running.", source
    )
    return None


def ensure_ca_bundle():
    """Point requests at a CA bundle that will still exist later. Never raises.

    Returns the path in use, or None when no bundle could be found at all - in
    which case outbound HTTPS is left to whatever requests works out for
    itself, exactly as before.
    """
    existing = os.environ.get("REQUESTS_CA_BUNDLE")
    if existing:
        if os.path.exists(existing):
            logger.info("Using the CA bundle from REQUESTS_CA_BUNDLE: %s", existing)
            return existing
        # Set but pointing at nothing: requests raises on every HTTPS call
        # rather than falling back, so this has to be corrected, not respected.
        logger.warning(
            "REQUESTS_CA_BUNDLE is set to a path that does not exist (%s) - "
            "replacing it.", existing
        )

    try:
        import certifi
        source = certifi.where()
    except Exception:
        logger.warning("certifi is not available; leaving TLS verification to requests.")
        return None

    if not os.path.exists(source):
        logger.error(
            "The bundled CA certificate file is missing (%s). Outbound HTTPS "
            "will fail until the application is reinstalled.", source
        )
        return None

    path = source
    if getattr(sys, "frozen", False):
        path = _writable_copy(source) or source

    os.environ["REQUESTS_CA_BUNDLE"] = path
    # urllib3 and anything else going through the stdlib read this one.
    os.environ.setdefault("SSL_CERT_FILE", path)

    logger.info("CA bundle: %s", path)
    return path
