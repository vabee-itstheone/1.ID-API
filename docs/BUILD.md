# Building and deploying

The API ships as a single Windows executable produced by PyInstaller.

---

## Prerequisites

- Python 3.13 (the version the current build was made with)
- **ODBC Driver 17 for SQL Server** installed on both the build and target machines
- Dependencies installed:

```bash
pip install -r requirements.txt
```

---

## Build

### Production build (windowless)

```bash
pyinstaller run.spec --noconfirm
```

Produces `dist\run.exe`. It runs with no console window - correct for a
background service, which is why the `/status` dashboard and `logs\` folder
exist.

**Stop the running instance before you build.** Windows locks a running
one-file exe, so PyInstaller cannot replace `dist\run.exe` while the API is up.
It fails with

```
PermissionError: [WinError 5] Access is denied: '...\dist\run.exe'
```

buried in the output - and then **exits 0 anyway**. The build looks like it
succeeded, `dist\run.exe` is still the previous binary, and that stale exe is
what gets deployed. Quit the API from its tray icon first, and after every
build confirm the timestamp actually moved:

```powershell
Get-Item dist\run.exe | Select-Object LastWriteTime, Length
```

If `/version` on a target machine still reports the old number after a deploy,
this is usually why.

### Diagnostic build (console visible)

```bash
pyinstaller run_console.spec --noconfirm
```

Produces `dist\run_console.exe`, which is identical except that it keeps a
console window open. Use it when the service will not start and nothing useful
reaches the log file.

Both specs list the same `hiddenimports`. **If you add a module that is only
imported dynamically, add it to both spec files** or PyInstaller will leave it
out and the exe will fail at runtime with `ModuleNotFoundError`.

`pystray._win32` in particular must stay listed. pystray selects its backend at
import time, which PyInstaller cannot follow - drop it and the build still
succeeds, but the exe starts with no tray icon and the only clue is a
"Could not create the tray icon" line in `logs\errors.log`.

---

## Before every build

1. Bump `__version__` in [`app/version.py`](../app/version.py). This is what
   `/version`, `/health` and the `/status` page report - if it does not change,
   there is no way to confirm a machine actually received the new build.
2. Check `requirements.txt` still matches your environment:

```bash
pip freeze | findstr /I "flask waitress sqlalchemy pyodbc pillow googletrans tzlocal requests"
```

---

## Deploy to a hotel machine

1. Copy `dist\run.exe` to the install folder, e.g. `C:\ITSthe1\API\`.
2. Copy `config.json` **next to the exe** and edit it for that site:
   - `SQLALCHEMY_DATABASE_URI` - that machine's SQL Server instance
   - `BaseDirectoryPath` - the document storage folder (created on first run if missing)
   - `PORT` - normally `5030`

   **Write every path with forward slashes** (`C:/ITSthe1/WPF/DOTS_Storage`).
   A pasted Windows path breaks the JSON - see the configuration section of
   [../README.md](../README.md). Validate before starting:

   ```powershell
   Get-Content config.json -Raw | ConvertFrom-Json
   ```
3. Start `run.exe`. A tray icon appears in the notification area; right-click it
   to open the status page or the logs, or to quit.
4. Open `http://localhost:5030/status` and confirm the banner is green and the
   version number matches what you just built.
5. Confirm the log file appeared: `C:\ITSthe1\API\logs\api.log`.

`config.json` is looked for next to the exe first, so each site keeps its own
settings and the same exe can be copied everywhere unchanged.

### Verifying a deployment landed

```powershell
(Invoke-RestMethod http://localhost:5030/version).version
```

```powershell
(Invoke-RestMethod http://localhost:5030/routes).count
```

If the version still reads the old number, the exe was not replaced - usually
because the old process was still running and holding the file.

### A stale instance no longer hides a new one

Windows lets two processes listen on the same port; the older one silently wins
every connection, so a freshly deployed exe can look like it started while
serving nothing. Since v1.0.0 the API checks the port before binding and
**refuses to start** if anything answers, logging to `logs\errors.log`:

```
CRITICAL Port 5030 is already in use on 127.0.0.1 - refusing to start.
```

Quit the running instance from its tray icon, or find it with
`netstat -ano | findstr :5030`, then start the new one.

---

## Running it as a Windows service

`run.exe` is a plain console-less program; it does not register itself as a
service. Two common approaches:

**Scheduled task** - trigger *At startup*, run whether the user is logged on or
not, action `C:\ITSthe1\API\run.exe`, arguments `--no-tray`, start-in
`C:\ITSthe1\API\`.

Pass `--no-tray` for either approach: a service runs in session 0 with no
desktop, so there is nowhere to draw a tray icon. The API detects this and
carries on without one regardless, but saying so explicitly keeps
`errors.log` free of the warning.

**NSSM** (Non-Sucking Service Manager) - wraps the exe as a real service with
automatic restart:

```bash
nssm install ITSthe1API C:\ITSthe1\API\run.exe
```

```bash
nssm set ITSthe1API AppDirectory C:\ITSthe1\API
```

Either way, verify afterwards by rebooting and then loading `/status`. The
**Uptime** tile should track time since the reboot; if it keeps resetting to a
few seconds the process is crash-looping, and `logs\errors.log` will say why.

---

## Firewall

If the WPF client runs on a different machine:

```powershell
New-NetFirewallRule -DisplayName "ITSthe1 ID API" -Direction Inbound -Protocol TCP -LocalPort 5030 -RemoteAddress 192.168.1.0/24 -Action Allow
```

Restrict `-RemoteAddress` to the subnet or specific client addresses. Never
expose port 5030 to the internet - the API has no authentication.

If the client is on the *same* machine, set `"HOST": "127.0.0.1"` in
`config.json` and no firewall rule is needed at all.

---

## Housekeeping

`dist.zip` in the repository root is an archived previous build (~37 MB). It is
not used at runtime and can be deleted once you are confident in the current
build.
