"""English -> Arabic name transliteration, and what to store when it fails.

The important part of this module is the failure path, not the happy one.

ArabicFirstName and ArabicLastName are ``nvarchar(45) NOT NULL``. The earlier
version of this helper returned the *error text* when the translator could not
be reached - ``"Exception: Could not find a suitable TLS CA certificate
bundle, invalid path: ..."`` - and the caller assigned that straight onto the
guest. Two things followed from it:

  - Anything longer than 45 characters made SQL Server reject the whole UPDATE
    with "String or binary data would be truncated" (error 8152), so a
    translator outage failed the entire check-in.
  - Anything *shorter* than 45 characters was accepted, and the guest was then
    stored - and reported onward - with an error message in place of a name.
    That is the worse of the two, because nothing surfaces it.

So a failure here never produces a value that pretends to be a translation.
The guest keeps their name in the Latin alphabet, the reason is logged, and the
check-in proceeds. Every return path is clamped to the column width, including
the successful one, because a long name transliterates to a long Arabic string.
"""

import logging

import requests

from app.config import Config

logger = logging.getLogger("itsthe1.api")

# Matches Guest.ArabicFirstName / Guest.ArabicLastName in app/models.py. Kept
# here rather than read off the model so this module stays importable without
# an application context.
MAX_NAME_LENGTH = 45

# The translator sits in a request that a receptionist is waiting on, with only
# a handful of waitress threads behind it. Without a timeout one unreachable
# host holds a thread until the OS gives up, and enough of them stop the API
# answering anything at all.
REQUEST_TIMEOUT_SECONDS = 5


def translate_to_arabic(english_text, max_length=MAX_NAME_LENGTH):
    """Transliterate a name into Arabic, falling back to the name as given.

    Returns a value that is always safe to assign to the Arabic name columns:
    never ``None``, never longer than ``max_length``, and never an error
    message. Callers do not need to check the result.
    """
    if not english_text:
        # NOT NULL columns, so the empty string rather than None.
        return ""

    source = str(english_text)
    fallback = source[:max_length]

    try:
        response = requests.get(
            f"{Config.GOOGLE_TRANSLATOR_URL}"
            f"?tlqt=1&langpair=en|ar&text={english_text}&&tl_app=1",
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:
            logger.warning(
                "Arabic transliteration of %r failed: HTTP %s. Storing the name "
                "as supplied.", source, response.status_code
            )
            return fallback

        json_result = response.json()
        first = json_result[0]
        translated = first["hws"][0] if "hws" in first else first["ew"]

    except (LookupError, TypeError, ValueError) as exc:
        # A 200 whose body is not the shape we expect - an interstitial page, a
        # changed API, an empty list.
        logger.warning(
            "Arabic transliteration of %r returned an unusable response (%s). "
            "Storing the name as supplied.", source, exc
        )
        return fallback

    except requests.RequestException as exc:
        # Unreachable host, TLS/CA problem, timeout. Expected on a site with no
        # outbound internet, so this must never be fatal.
        logger.warning(
            "Arabic transliteration of %r could not reach %s (%s). Storing the "
            "name as supplied.", source, Config.GOOGLE_TRANSLATOR_URL, exc
        )
        return fallback

    except Exception:
        logger.exception(
            "Arabic transliteration of %r failed unexpectedly. Storing the name "
            "as supplied.", source
        )
        return fallback

    if not translated:
        return fallback

    translated = str(translated)
    if len(translated) > max_length:
        logger.warning(
            "Arabic transliteration of %r is %s characters and does not fit "
            "%s - truncating.", source, len(translated), max_length
        )

    return translated[:max_length]
