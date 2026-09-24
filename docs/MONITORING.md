# Monitoring - how to tell whether the API is working

`run.exe` is built windowless: no console, no tray icon, no visible sign of life.
This page describes the four ways to check on it, from easiest to most detailed.

---

## 1. The status dashboard (start here)

Open in any browser on the machine:

```
http://localhost:5030/status
```

The page refreshes itself every 5 seconds. No installation, no tools - it is
served by the API itself.

### Reading the banner

| Banner | Meaning | What to do |
|---|---|---|
| 🟢 **API is running normally** | Process is up and all checks pass. | Nothing. |
| 🔴 **API is up, but a dependency is broken** | The API answers, but the database, storage folder or `config.json` failed its check. | Read the **System checks** panel - it names the exact failure. |
| 🔴 **Cannot reach the API** | Nothing answered on the port. | The process is not running, crashed, or is on a different port. See [Troubleshooting](#troubleshooting). |
| 🟡 **API is up and responding** | Shown briefly on first load while the database check runs. | Wait a few seconds. |

The tiles below the banner show:

| Tile | Meaning |
|---|---|
| **Uptime** | How long this process has been running. A number that keeps resetting means the service is crash-looping. |
| **Requests served** | Business requests handled since startup. Monitoring traffic is excluded, so this is real client activity. If the WPF app is in use and this stays at 0, the client is not reaching the API. |
| **Failed responses** | Requests that failed - including ones that returned HTTP 200 with an error inside (see below). |
| **DB response** | Round-trip time of a `SELECT 1`, or `unreachable`. |
| **Host / Process ID** | Which machine and which process, for confirming you are looking at the right instance. |

Then:

- **System checks** - config file, database and storage folder, each with the exact error text.
- **Recent requests** - the last 50 calls with method, path, status code and duration.
- **Recent errors** - the same list filtered to failures only.
- **Busiest endpoints** - which calls the client is actually making.

### The "200 OK but actually broken" case

The reference lookup endpoints (`/country`, `/room`, …) catch their own database
errors and return **HTTP 200** with a body of `{"error": "..."}`. To anything
watching status codes that looks like success.

The dashboard detects this: any 2xx response whose body contains `error` or
`hasErrors: true` is counted as a **failed response** and shown in red in the
request table with the underlying message. This is usually the first visible sign
that SQL Server has gone away.

---

## 2. The health endpoint (for scripts and monitoring tools)

```
GET http://localhost:5030/health
```

Returns **200** when healthy and **503** when any check fails, so it can be
wired into any uptime monitor.

```json
{
  "status": "healthy",
  "healthy": true,
  "name": "ITSthe1.ID API",
  "version": "1.0.0",
  "host": "FRONTDESK-01",
  "pid": 9764,
  "port": 5030,
  "startedAt": "2026-08-03T07:59:15+00:00",
  "uptimeHuman": "3h 12m 4s",
  "totalRequests": 1841,
  "totalErrors": 0,
  "logDirectory": "C:\\ITSthe1\\API\\logs",
  "checks": {
    "config":   { "ok": true, "file": "C:\\ITSthe1\\API\\config.json", "error": null },
    "database": { "ok": true, "latencyMs": 4.1, "uri": "mssql+pyodbc://sa:***@…", "schema": "[dots.id].[itsthe1.id]", "error": null },
    "storage":  { "ok": true, "path": "C:/ITSthe1/WPF/DOTS_Storage", "error": null }
  }
}
```

| Check | Passes when |
|---|---|
| `config` | `config.json` was found and parsed. |
| `database` | `SELECT 1` succeeded against the configured connection. |
| `storage` | `BaseDirectoryPath` exists and a test file can be written and deleted. |

Add `?deep=false` to skip the database and storage probes. That variant answers
in under a millisecond even when SQL Server is down, so it is the right choice
for a liveness probe that must not block.

### Other endpoints

| Endpoint | Returns |
|---|---|
| `GET /ping` | `pong` as plain text. No database access. |
| `GET /version` | Version, PID, Python version, start time, whether it is the packaged build. |
| `GET /metrics` | All counters plus the recent request and error lists as JSON. |
| `POST /metrics/reset` | Zeroes the counters without restarting the service. |
| `GET /routes` | Every URL this build serves - use it to confirm a deployment actually contains a new endpoint. |
| `GET /` | One-line summary with links to the above. |

---

## 3. The command line

From PowerShell on the API machine:

```powershell
.\check_api.ps1
```

It prints a pass/fail summary and exits with code `0` when healthy and `1` when
not, so it can be used in a scheduled task. Point it elsewhere with
`.\check_api.ps1 -Port 5030 -ApiHost 192.168.1.50`.

Ad-hoc equivalents:

```bash
curl http://localhost:5030/ping
```

```powershell
(Invoke-WebRequest http://localhost:5030/health).Content
```

To confirm the process is listening at all:

```powershell
netstat -ano | findstr :5030
```

---

## 4. The log files

Written to `logs\` beside `run.exe` (override with `LOG_DIR` in `config.json`):

| File | Contents |
|---|---|
| `api.log` | Everything: startup banner, every request, every error. |
| `errors.log` | `WARNING` and above only - check this one first. |

Both roll over at 5 MB and keep 5 previous files (`api.log.1`, `api.log.2`, …).

A healthy startup looks like this:

```
2026-08-03 13:29:16 INFO  [itsthe1.api] ==============================================
2026-08-03 13:29:16 INFO  [itsthe1.api] ITSthe1.ID API v1.0.0 starting
2026-08-03 13:29:16 INFO  [itsthe1.api] Listening on   : http://0.0.0.0:5030
2026-08-03 13:29:16 INFO  [itsthe1.api] Health check   : http://127.0.0.1:5030/health
2026-08-03 13:29:16 INFO  [itsthe1.api] Status page    : http://127.0.0.1:5030/status
2026-08-03 13:29:16 INFO  [itsthe1.api] Config file    : C:\ITSthe1\API\config.json
2026-08-03 13:29:16 INFO  [itsthe1.api] Database       : mssql+pyodbc://sa:***@FRONTDESK-01\WPFSQLEXPRESS/dots.id
2026-08-03 13:29:16 INFO  [itsthe1.api] Schema         : [dots.id].[itsthe1.id]
2026-08-03 13:29:16 INFO  [itsthe1.api] ==============================================
```

Individual requests are logged as:

```
2026-08-03 13:32:39 INFO     [itsthe1.api.monitoring] POST /checkin -> 200 (412 ms) from 192.168.1.44
2026-08-03 13:32:44 WARNING  [itsthe1.api.monitoring] POST /checkin -> 400 (18 ms) from 192.168.1.44 | general: 40002 Checkin room does not exist
```

Follow the log live:

```powershell
Get-Content .\logs\api.log -Wait -Tail 20
```

Notes:

- Monitoring requests (`/status`, `/health`, `/metrics`, …) are **not** logged,
  so a browser left open on the dashboard does not bury real traffic.
- A repeating database failure is logged once every 5 minutes with a count of
  suppressed duplicates, rather than on every check.

---

## Troubleshooting

### The dashboard says "Cannot reach the API"

1. Is the process running? `Get-Process run -ErrorAction SilentlyContinue`
2. Is anything listening? `netstat -ano | findstr :5030`
3. Does `logs\api.log` end with a startup banner, or with an error?
4. Is the port right? The banner in `api.log` states the real port.

### It will not start, and nothing is in the log

The log directory may not be writable, or the failure happens before logging
starts. Build and run the console version, which prints straight to a window:

```bash
pyinstaller run_console.spec --noconfirm
```

```bash
dist\run_console.exe
```

### "Could not bind to 0.0.0.0:5030"

Another process already owns the port - most often a previous `run.exe` that did
not exit. Find and stop it:

```powershell
netstat -ano | findstr :5030
```

```powershell
Stop-Process -Id <PID>
```

### The API answers but every call is slow and returns errors

The database is unreachable. Confirm on `/status` under **System checks**; the
`database` row carries the raw ODBC error. Common causes:

- SQL Server service is stopped
- the instance name in `SQLALCHEMY_DATABASE_URI` is wrong (backslashes must be doubled: `HOST\\WPFSQLEXPRESS`)
- SQL Server TCP/IP is disabled, or the SQL Browser service is not running
- ODBC Driver 17 for SQL Server is not installed on the machine

### The status page shows 0 requests while staff are using the app

The WPF client is not reaching this API. Check the client's configured address
and port, and confirm the firewall allows the client machine to reach port 5030.

### Health says unhealthy because of `storage`

`BaseDirectoryPath` does not exist or is not writable. Create the folder or fix
its permissions; guest document uploads will fail until then.
