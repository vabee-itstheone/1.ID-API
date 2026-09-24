# ITSthe1.ID API

A Flask REST API that records hotel guest check-ins, check-outs, room changes and
guest documents into a SQL Server database, following the
**1.ID API Specification Document**.

It is packaged as a single Windows executable (`dist/run.exe`) and normally runs
as a background service on the hotel's front-desk machine, serving the
ITSthe1.ID WPF desktop application.

| | |
|---|---|
| Default port | `5030` (set in `config.json`) |
| Database | SQL Server via `pyodbc` / SQLAlchemy |
| Server | Waitress (production WSGI server) |
| **Is it working?** | **Open <http://localhost:5030/status> in a browser** |

---

## Documentation map

| Document | What it covers |
|---|---|
| **This file** | How the API works, quick start, configuration |
| **ITSthe1.ID API Integration Specification v1.0.0** (`.docx` / `.pdf` in `docs/`) | **The formal specification to send a partner developer** - 40 pages, structured like the 1.ID API Specification Document: every endpoint with its payload, validation order, response and error codes, plus appendices on spec deviations, known issues, environment setup and security |
| [docs/PARTNER_HANDOVER.md](docs/PARTNER_HANDOVER.md) | **Integration handover report** - give this to an external developer. Environment setup, verification status, the known-issues register, and what the integration contract actually is |
| [docs/SPEC_CONFORMANCE.md](docs/SPEC_CONFORMANCE.md) | **This build vs the 1.ID API Specification Document** - endpoint coverage, unimplemented spec error codes, validation rules that differ |
| [docs/MONITORING.md](docs/MONITORING.md) | **How to tell whether it is running** - the status dashboard, health checks, logs, troubleshooting |
| [docs/API.md](docs/API.md) | Every endpoint: request bodies, responses, error codes |
| [docs/PAYLOADS.md](docs/PAYLOADS.md) | **Ready-to-send payloads for every endpoint**, including escorts - plus `docs/payloads/` with the JSON files, a 61-request Postman collection and two runner scripts |
| [docs/BUILD.md](docs/BUILD.md) | Building `run.exe` and deploying it to a hotel machine |

---

## Quick start

### Run from source

```bash
pip install -r requirements.txt
```

```bash
python run.py
```

Then confirm it is alive:

```bash
curl http://localhost:5030/ping
```

…or just open <http://localhost:5030/status> in a browser.

### Run the built executable

```bash
dist\run.exe
```

`run.exe` shows no console window, but it does put a **system tray icon** in the
notification area. Right-click it for:

| Menu item | Does |
|---|---|
| Open status page | Opens `http://127.0.0.1:5030/status` in your browser |
| Open log folder | Opens the `logs\` folder in Explorer |
| Refresh health | Re-checks now instead of waiting for the 30 s poll |
| Start with Windows | Ticked when the API starts at logon. Click to turn it on or off |
| **Quit** | Stops the server cleanly - no Task Manager needed |

The icon is a dot that tracks health: **green** when every check passes, **red**
when one fails, grey until the first check completes. Hovering shows the version
and the address it is listening on.

Pass `--no-tray` to run without it - correct for a Windows service or scheduled
task, which has no desktop to draw on. The API also falls back to this
automatically if a tray cannot be created, so a service install still works.

See [docs/MONITORING.md](docs/MONITORING.md).

### Starting with Windows

On by default: the first normal (tray) start writes a per-user logon entry, so
the API comes back up whenever the operator signs in. No admin rights, no
service install, no scheduled task.

```
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
    "ITSthe1.ID API" = "C:\path\to\run.exe"
```

Two ways to change it, and they stay in step - the tray writes the setting back
to `config.json`, and every start re-applies `config.json` to the registry:

* **Tray icon** → *Start with Windows* (takes effect immediately)
* **`config.json`** → `"StartWithWindows": false` (takes effect on next start)

Each start also rewrites the command, so moving or rebuilding `run.exe` fixes
the entry by itself. `--no-tray` skips all of this: a service or scheduled task
is already started by Windows, and a second logon copy would fight it for the
port.

Check it from PowerShell:

```bash
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ITSthe1.ID API"
```

---

## How the API works

### Request lifecycle

```
WPF client
    │  HTTP JSON  (POST /checkin, GET /country, …)
    ▼
Waitress  (production WSGI server, 8 threads)
    ▼
Flask app  ──▶ before_request : start a timer
    ▼
Blueprint route  (app/<feature>/routes.py)
    │   • validates the payload against the 1.ID spec
    │   • calls services.py for read-only lookups
    │   • writes rows through SQLAlchemy models (app/models.py)
    ▼
SQL Server   schema [dots.id].[itsthe1.id]
    ▲
    │  JSON response  { hasErrors, errorMessages, messageUID, … }
    ▼
Flask app  ──▶ after_request : record metrics, write the access log
    ▼
WPF client
```

### Project layout

```
my_flask_app_4_new_database/
├─ run.py                 Entry point: starts Waitress, prints the startup banner
├─ run.spec               PyInstaller recipe (windowless production build)
├─ run_console.spec       PyInstaller recipe (console build, for diagnosing)
├─ config.json            All deployment settings. Read at startup.
├─ requirements.txt       Python dependencies
├─ check_api.ps1          One-command health check from PowerShell
├─ logs/                  Rotating log files (created on first run)
├─ docs/                  API, monitoring and build documentation
└─ app/
   ├─ __init__.py         create_app(): builds the Flask app, registers blueprints
   ├─ config.py           Loads config.json, exposes the Config class
   ├─ models.py           SQLAlchemy models - one class per database table
   ├─ version.py          The version number reported by /version and /status
   ├─ logging_setup.py    Rotating file + console logging
   ├─ tray.py             System tray icon for the windowless build
   ├─ autostart.py        "Start with Windows" - the per-user logon entry
   ├─ monitoring/         Health checks, metrics, /status dashboard
   ├─ changes/            GET /changes - the cheap "has anything changed?" feed
   ├─ utilities/          Image resizing, gzip/ETag, the shared table reader
   ├─ checkin/            ─┐
   ├─ checkout/            │ One package per feature. Each contains:
   ├─ guest/               │   routes.py     - HTTP endpoints + validation
   ├─ roomchange/          │   services.py   - database reads
   ├─ country/             │   validators.py - shared validation (some packages)
   └─ …23 more             ─┘
```

### The two kinds of endpoint

**1. Reference lookups** - simple `GET`s that return a whole table. Used by the
WPF client to populate dropdowns.

`/country` `/emirate` `/room` `/documenttype` `/visitpurpose` `/relationship`
`/paymenttype` `/cardtype` `/checkintype` `/checkouttype` `/escorttype`
`/accessibilitytype` `/cancellationreason` `/dtcmaction` `/log` and others.

**2. Business transactions** - `POST`/`PUT` endpoints that implement the 1.ID
specification, each running a long list of numbered validations before writing
anything.

`/checkin` `/checkout` `/checkincancellation` `/guest` `/guestcheckout`
`/guestattachment` `/roomchange`

Every business endpoint answers with the spec's envelope:

```json
{
  "hasErrors": false,
  "errorMessages": {},
  "messageType": "CheckinResponse",
  "clientUID": "Establishment101",
  "messageUID": "7230ad75-8a9f-45c0-a000-ddb587c66345",
  "correlationUID": "f50a8b4d",
  "timestamp": "2025-02-17T11:40:01.125047+05:30"
}
```

Validation failures return HTTP 400 with `hasErrors: true` and a numbered code
such as `40002 Checkin room does not exist`. The full list is in
[docs/API.md](docs/API.md).

**3. The change feed** - `GET /changes`, the endpoint a client polls instead of
re-reading tables.

A whole-table `GET` is a fine way to load a dropdown and a terrible way to
notice a check-out. On a hotel a year into service `GET /log` alone is 99,722
rows and 27 MB, and a client that refreshes by re-reading every table moves
about **109 MB** before it can show that room 101 went vacant - which is why a
141 ms `POST /checkout` used to take over a minute to appear on screen.

`/changes` answers the same question from index reads and a checksum over the
59-row room table:

```bash
curl "http://localhost:5030/changes?since=<revision>&wait=25"
```

It returns in ~2 ms, or - with `wait` - holds the connection open and answers
within about 250 ms of the commit. `changedTables` then says which tables to
re-read, and every table endpoint takes `?since_id=` so the re-read is the rows
that are new rather than all of them. A check-out refresh done this way costs
**27 ms and ~2 KB** instead of 8.3 seconds and 102 MB.

Two smaller savings need no client change at all: responses over 4 KB are
gzipped when the caller advertises it (5-9x smaller) and carry an `ETag`, so a
client that sends `If-None-Match` gets a 304 with no body when a table has not
moved. Full detail in
[docs/API.md](docs/API.md#staying-up-to-date).

### Monitoring endpoints

Added so you can see the API working without reading the database:

| Endpoint | Purpose |
|---|---|
| `GET /status` | **Live HTML dashboard** - open this in a browser |
| `GET /health` | Full readiness check (database + storage + config); 200 or 503 |
| `GET /ping` | Cheapest liveness check, returns `pong` |
| `GET /version` | Version, PID, start time |
| `GET /metrics` | Request counters and recent traffic as JSON |
| `GET /routes` | Every URL this build serves |

See [docs/MONITORING.md](docs/MONITORING.md).

---

## Configuration

Everything lives in `config.json`, next to `run.py` (source) or next to
`run.exe` (deployed). It is read once at startup - **restart after editing.**

```json
{
  "SQLALCHEMY_DATABASE_URI": "mssql+pyodbc://USER:PASSWORD@HOSTNAME\\WPFSQLEXPRESS/dots.id?driver=ODBC+Driver+17+for+SQL+Server",
  "SCHEMA_NAME": "[dots.id].[itsthe1.id]",
  "BaseDirectoryPath": "C:/ITSthe1/WPF/DOTS_Storage",
  "GOOGLE_TRANSLATOR_URL": "https://google.com/transliterate/indic",
  "HOST": "0.0.0.0",
  "PORT": 5030,
  "StartWithWindows": true,
  "LOG_LEVEL": "INFO",
  "LOG_MAX_BYTES": 5242880,
  "LOG_BACKUP_COUNT": 5,
  "REQUEST_HISTORY_SIZE": 50
}
```

| Key | Default | Meaning |
|---|---|---|
| `SQLALCHEMY_DATABASE_URI` | `sqlite:///default.db` | SQL Server connection string. Backslashes in the instance name must be doubled (`\\`). |
| `SCHEMA_NAME` | `[default_schema]` | Database + schema prefix applied to every table. |
| `BaseDirectoryPath` | `C:/DefaultPath` | Folder where guest document images are stored. |
| `GOOGLE_TRANSLATOR_URL` | Google transliterate | Used to romanise/transliterate Arabic guest names. |
| `HOST` | `0.0.0.0` | Interface to bind. `0.0.0.0` = all; `127.0.0.1` = this machine only. |
| `PORT` | `5000` | Listening port. |
| `StartWithWindows` | `true` | Start the API when the operator logs in. Also toggled from the tray icon, which writes the change back here. Ignored with `--no-tray`. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR`. |
| `LOG_MAX_BYTES` | `5242880` | Size at which a log file rolls over (5 MB). |
| `LOG_BACKUP_COUNT` | `5` | Number of rolled log files to keep. |
| `REQUEST_HISTORY_SIZE` | `50` | Recent requests kept in memory for `/status`. |
| `DB_CONNECT_TIMEOUT` | `5` | Seconds to wait when opening a SQL Server connection. |

### Paths: use forward slashes

`config.json` is JSON, and JSON treats `\` as an escape character. A pasted
Windows path therefore breaks the file:

```json
"BaseDirectoryPath": "C:\ITSthe1\WPF\DOTS_Storage"
```

```
Invalid \escape: line 4 column 27
```

Worse, some paths break *silently*: every separator in `C:\build\files` happens
to begin a legal escape (`\b`, `\f`), so the file parses without complaint and
decodes to `C:\x08uild\x0ciles` - and the only symptom is a storage directory
that "does not exist".

**Always write paths with forward slashes**, which Windows accepts everywhere:

```json
"BaseDirectoryPath": "C:/ITSthe1/WPF/DOTS_Storage"
```

Doubled backslashes (`C:\\ITSthe1\\WPF`) also work. The same applies to a named
SQL Server instance in `SQLALCHEMY_DATABASE_URI`: `HOST\\SQLEXPRESS`.

Since v1.0.0 the API detects both mistakes, repairs the values in memory so the
instance still starts correctly, and reports what it did as a **warning** on
`/health` and the `/status` dashboard. The repair is a safety net, not a
licence to leave the file broken - fix it and the warning goes away.

Check a file before restarting:

```powershell
Get-Content config.json -Raw | ConvertFrom-Json
```

### Search order

`config.json` is searched for in this order, first match wins:

1. next to `run.exe` (packaged builds only)
2. the project root
3. the `app/` folder
4. the current working directory

If none is found the API still starts, but falls back to an empty SQLite
database. `GET /health` reports this explicitly under `checks.config`, and the
`/status` dashboard shows it in red - so a missing config file can no longer be
mistaken for a working install.

---

## Security note

The API has **no authentication**. Anything that can reach the port can create
check-ins and read guest data. It is designed to run on a closed hotel LAN.

- Keep `HOST` as `127.0.0.1` if the WPF client runs on the same machine as the API.
- If the client is on another machine, restrict port 5030 with a Windows
  Firewall rule to the specific client addresses.
- Do not expose this port to the internet.

The database password appears in plain text in `config.json`; protect that file
with NTFS permissions. It is masked (`sa:***`) everywhere the API reports its
own configuration.
