import os
import sys
import json


def _candidate_config_paths():
    """Every place we are willing to look for config.json, in priority order.

    When frozen by PyInstaller the exe folder wins, because that is where the
    operator drops the file next to run.exe. When running from source the
    project root wins, because that is where config.json lives in the repo.
    """
    paths = []

    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        paths.append(os.path.join(exe_dir, "config.json"))

    app_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(app_dir)

    paths.append(os.path.join(project_root, "config.json"))
    paths.append(os.path.join(app_dir, "config.json"))
    paths.append(os.path.join(os.getcwd(), "config.json"))

    # De-duplicate while preserving order.
    seen = set()
    unique = []
    for path in paths:
        normalised = os.path.normcase(os.path.abspath(path))
        if normalised not in seen:
            seen.add(normalised)
            unique.append(path)
    return unique


# Escapes JSON actually understands. A backslash followed by anything else is a
# syntax error - which is exactly what a pasted Windows path produces.
_VALID_JSON_ESCAPES = set('"\\/bfnrtu')

# Escapes that carry structure rather than data. These must survive even the
# aggressive repair, or quoted strings and unicode literals would break.
_STRUCTURAL_ESCAPES = set('"\\/u')


def _repair_windows_paths(text, aggressive=False):
    """Double up backslashes that JSON would reject, and report what changed.

    Operators paste Windows paths straight into config.json:

        "BaseDirectoryPath": "C:\\ITSthe1\\WPF\\DOTS_Storage"

    which json.load rejects with ``Invalid \\escape``. Worse, a path like
    ``C:\\temp`` parses *successfully* into a string containing a TAB, and the
    failure only shows up later as a missing directory.

    So: inside string literals, any backslash that does not begin a valid JSON
    escape is doubled. ``\\\\`` is left alone (already correct), and ``\\u`` is
    left alone so real unicode escapes survive.

    ``aggressive`` additionally rewrites backslashes that *are* valid escapes
    (``\\b \\f \\n \\r \\t``). Those are the silent case - ``C:\\build\\files``
    is legal JSON that decodes to control characters - so this mode is used only
    once such a value has actually been spotted. Structural escapes (``\\\\``,
    ``\\"``, ``\\/``, ``\\uXXXX``) are always preserved.

    Returns (repaired_text, count).
    """
    safe = _STRUCTURAL_ESCAPES if aggressive else _VALID_JSON_ESCAPES

    out = []
    in_string = False
    repairs = 0
    i = 0
    while i < len(text):
        ch = text[i]

        if not in_string:
            if ch == '"':
                in_string = True
            out.append(ch)
            i += 1
            continue

        if ch == '"':
            in_string = False
            out.append(ch)
            i += 1
            continue

        if ch == "\\":
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if nxt == "\\":
                # Already escaped - copy the pair through untouched.
                out.append("\\\\")
                i += 2
                continue
            if nxt in safe:
                out.append(ch)
                i += 1
                continue
            # A backslash that was meant literally - escape it.
            out.append("\\\\")
            repairs += 1
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out), repairs


# Control characters that a Windows path can never legitimately contain. Their
# presence means a backslash was eaten as an escape: "C:\build" -> "C:\x08uild".
_CONTROL_CHARS = "\b\f\n\r\t\v\a"


def _has_mangled_path(cfg):
    """True when a parsed value contains a control character.

    The nastiest form of the backslash problem parses *cleanly*. Every
    separator in ``C:\\build\\files`` happens to begin a valid JSON escape, so
    json.loads returns ``C:\\x08uild\\x0ciles`` with no error at all, and the
    only symptom is a storage directory that mysteriously does not exist.
    """
    return any(
        isinstance(v, str) and any(c in v for c in _CONTROL_CHARS)
        for v in cfg.values()
    )


def _load_config():
    """Return (config_dict, path_used, error_message, warning_message).

    ``error`` means nothing was loaded and the defaults are in force - the API
    is misconfigured. ``warning`` means the settings *were* loaded but the file
    needs attention.
    """
    for path in _candidate_config_paths():
        if not os.path.exists(path):
            continue

        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                raw = f.read()
        except Exception as exc:  # permissions, locked file, bad encoding
            return {}, path, f"Could not read {path}: {exc}", None

        _FIX_HINT = ("Fix the file with forward slashes "
                     "(C:/ITSthe1/WPF/DOTS_Storage) or doubled backslashes.")

        try:
            cfg = json.loads(raw)
        except json.JSONDecodeError as exc:
            # Invalid JSON. Before giving up, try the mistake that accounts for
            # nearly every malformed config we see: un-escaped Windows paths.
            repaired, count = _repair_windows_paths(raw)
            if count:
                try:
                    cfg = json.loads(repaired)
                except json.JSONDecodeError:
                    pass
                else:
                    return cfg, path, None, (
                        f"{path} is not valid JSON - it contains {count} un-escaped "
                        f"backslash(es), so it was loaded using an automatic repair. "
                        f"{_FIX_HINT}"
                    )
            return {}, path, f"Could not read {path}: {exc}", None

        if not _has_mangled_path(cfg):
            return cfg, path, None, None

        # Valid JSON, but a value decoded to control characters - the silent
        # form of the same mistake. Repair aggressively and prefer that reading,
        # because it is what the operator meant.
        repaired, count = _repair_windows_paths(raw, aggressive=True)
        if count:
            try:
                fixed = json.loads(repaired)
            except json.JSONDecodeError:
                pass
            else:
                return fixed, path, None, (
                    f"{path} is valid JSON, but {count} backslash(es) were being "
                    f"read as escape characters (\\b, \\t, \\f...), silently "
                    f"corrupting the paths. They were repaired automatically. "
                    f"{_FIX_HINT}"
                )

        return cfg, path, None, (
            f"{path} contains a value with control characters, probably a Windows "
            f"path whose backslashes were read as escapes. {_FIX_HINT}"
        )

    searched = ", ".join(_candidate_config_paths())
    return {}, None, f"config.json not found. Searched: {searched}", None


_cfg, _cfg_path, _cfg_error, _cfg_warning = _load_config()

if _cfg_error:
    print(f"[WARNING] {_cfg_error}")
if _cfg_warning:
    print(f"[WARNING] {_cfg_warning}")


class Config:
    # Detect base directory (works for both Python and PyInstaller .exe)
    if getattr(sys, 'frozen', False):
        BASE_DIR = os.path.dirname(sys.executable)
    else:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Which config.json actually got loaded, and why it failed if it did not.
    # Surfaced by /health so a misconfigured instance is obvious.
    CONFIG_FILE = _cfg_path
    CONFIG_ERROR = _cfg_error
    # Set when the settings loaded but the file still needs fixing.
    CONFIG_WARNING = _cfg_warning

    SQLALCHEMY_DATABASE_URI = _cfg.get("SQLALCHEMY_DATABASE_URI", "sqlite:///default.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCHEMA_NAME = _cfg.get("SCHEMA_NAME", "[default_schema]")
    BaseDirectoryPath = _cfg.get("BaseDirectoryPath", "C:/DefaultPath")
    GOOGLE_TRANSLATOR_URL = _cfg.get(
        "GOOGLE_TRANSLATOR_URL",
        "https://google.com/transliterate/indic"
    )

    # Where a guest's document images are kept. The two 1.ID deployments differ:
    # a DOTS site keeps the bytes in SQL Server as well as on disk, an ordinary
    # hotel keeps them only under BaseDirectoryPath.
    #
    #   "database"   - write the guestdocumentimages row (DOTS)
    #   "filesystem" - disk only, never touch guestdocumentimages
    #   "auto"       - try the row, and fall back to disk for the rest of the
    #                  process the first time the table turns out to be absent
    #
    # "auto" is the default so a hotel database without the table still accepts
    # check-ins instead of answering 500 on every write.
    DOCUMENT_IMAGE_STORAGE = str(
        _cfg.get("DocumentImageStorage", "auto")
    ).strip().lower()
    PORT = _cfg.get("PORT", 5000)   # default port = 5000
    HOST = _cfg.get("HOST", "0.0.0.0")

    # Start the API when the operator logs in. Mirrored into the Windows Run key
    # at startup and toggled from the tray icon - see app/autostart.py.
    START_WITH_WINDOWS = bool(_cfg.get("StartWithWindows", True))

    # Seconds to wait when opening a SQL Server connection. Without this a
    # request thread blocks on the ODBC default (~15-30s) whenever the database
    # server is down, which makes the whole API look hung.
    DB_CONNECT_TIMEOUT = int(_cfg.get("DB_CONNECT_TIMEOUT", 5))

    SQLALCHEMY_ENGINE_OPTIONS = {
        # Verify a pooled connection is still alive before handing it out.
        # Prevents "connection reset" errors after the DB or network blips.
        "pool_pre_ping": True,
    }
    if SQLALCHEMY_DATABASE_URI.startswith("mssql"):
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"] = {"timeout": DB_CONNECT_TIMEOUT}

    # --- Logging / monitoring -------------------------------------------------
    # The production build runs windowless (console=False), so the log file is
    # the only place stdout would otherwise have gone.
    LOG_DIR = _cfg.get("LOG_DIR", os.path.join(BASE_DIR, "logs"))
    LOG_LEVEL = _cfg.get("LOG_LEVEL", "INFO")
    LOG_MAX_BYTES = int(_cfg.get("LOG_MAX_BYTES", 5 * 1024 * 1024))
    LOG_BACKUP_COUNT = int(_cfg.get("LOG_BACKUP_COUNT", 5))
    # How many recent requests the /status dashboard keeps in memory.
    REQUEST_HISTORY_SIZE = int(_cfg.get("REQUEST_HISTORY_SIZE", 50))

    @classmethod
    def safe_database_uri(cls):
        """Database URI with the password masked, safe to show in /health."""
        uri = cls.SQLALCHEMY_DATABASE_URI or ""
        if "://" not in uri:
            return uri
        scheme, _, rest = uri.partition("://")
        if "@" not in rest:
            return uri
        credentials, _, host_part = rest.partition("@")
        user, sep, _password = credentials.partition(":")
        if sep:
            credentials = f"{user}:***"
        return f"{scheme}://{credentials}@{host_part}"


def save_setting(name, value):
    """Write one setting back into the config.json that was loaded.

    Used by the tray icon, which changes a setting while the API is running.
    The file is re-read first so anything edited by hand since startup survives,
    and a file that will not parse is never overwritten - rewriting it would
    silently replace the operator's settings with defaults.

    Returns the path written. Raises RuntimeError when there is nothing safe to
    write to.
    """
    cfg, path, error, _warning = _load_config()
    if error or not path:
        raise RuntimeError(error or "config.json was not found")

    cfg[name] = value

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(cfg, handle, indent=2)
        handle.write("\n")

    _cfg[name] = value  # keep the in-process copy in step with the file
    return path
