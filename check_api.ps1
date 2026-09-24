<#
.SYNOPSIS
    Checks whether the ITSthe1.ID API is running and healthy.

.DESCRIPTION
    Prints a pass/fail summary of the API's liveness, version and dependency
    checks. Exits 0 when healthy and 1 when not, so it can be used from a
    scheduled task or a monitoring agent.

.EXAMPLE
    .\check_api.ps1

.EXAMPLE
    .\check_api.ps1 -ApiHost 192.168.1.50 -Port 5030
#>
[CmdletBinding()]
param(
    [string] $ApiHost = "localhost",
    [int]    $Port    = 5030,
    [int]    $TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$base = "http://${ApiHost}:${Port}"

function Write-Line([string] $Mark, [string] $Text, [string] $Colour) {
    Write-Host ("  {0} {1}" -f $Mark, $Text) -ForegroundColor $Colour
}

Write-Host ""
Write-Host "ITSthe1.ID API health check - $base" -ForegroundColor Cyan
Write-Host ("-" * 60)

# --- 1. Is anything listening? ------------------------------------------------
try {
    $ping = Invoke-WebRequest -Uri "$base/ping" -TimeoutSec 10 -UseBasicParsing
    if ($ping.Content.Trim() -ne "pong") { throw "Unexpected reply: $($ping.Content)" }
    Write-Line "[OK]" "API is listening and responding" Green
}
catch {
    Write-Line "[FAIL]" "No response from $base" Red
    Write-Host ""
    Write-Host "  The API is not running, or is on a different port." -ForegroundColor Yellow
    Write-Host "  Check what is listening:  netstat -ano | findstr :$Port" -ForegroundColor Yellow
    Write-Host "  Then read the log:        Get-Content .\logs\errors.log -Tail 30" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# --- 2. Version ---------------------------------------------------------------
try {
    $v = Invoke-RestMethod -Uri "$base/version" -TimeoutSec 10
    Write-Line "[OK]" ("Version {0}  (PID {1}, Python {2}, started {3})" -f `
        $v.version, $v.pid, $v.python, $v.startedAt) Green
}
catch {
    Write-Line "[WARN]" "Could not read /version" Yellow
}

# --- 3. Full health -----------------------------------------------------------
# The deep check contacts SQL Server, so allow a generous timeout.
# An unhealthy API answers 503, which Invoke-RestMethod raises as a terminating
# error even though the body is exactly what we want - so read it back out.
$healthy = $true
$h = $null
try {
    $h = Invoke-RestMethod -Uri "$base/health" -TimeoutSec $TimeoutSeconds
}
catch {
    $body = $null

    # PowerShell 5.1 puts the response body here for failed web requests.
    if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
        $body = $_.ErrorDetails.Message
    }
    elseif ($_.Exception.Response) {
        try {
            $stream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($stream)
            $body = $reader.ReadToEnd()
            $reader.Close()
        } catch { }
    }

    if ($body) {
        try { $h = $body | ConvertFrom-Json } catch { $h = $null }
    }

    if (-not $h) {
        Write-Line "[FAIL]" "Health check did not complete: $($_.Exception.Message)" Red
        Write-Host ""
        exit 1
    }
}

# Never report success on a response we could not interpret.
if (-not $h.checks) {
    Write-Line "[FAIL]" "/health returned no checks - cannot confirm the API is healthy" Red
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "  Uptime          : $($h.uptimeHuman)"
Write-Host "  Requests served : $($h.totalRequests)"
Write-Host "  Failed          : $($h.totalErrors)"
Write-Host "  Log directory   : $($h.logDirectory)"
Write-Host ""

foreach ($name in $h.checks.PSObject.Properties.Name) {
    $check = $h.checks.$name
    if ($check.ok) {
        $detail = if ($check.latencyMs) { "$($check.latencyMs) ms" }
                  elseif ($check.path)  { $check.path }
                  elseif ($check.file)  { $check.file }
                  else                  { "OK" }
        Write-Line "[OK]" ("{0,-10} {1}" -f $name, $detail) Green
    }
    else {
        $healthy = $false
        Write-Line "[FAIL]" ("{0,-10} {1}" -f $name, $check.error) Red
    }
}

Write-Host ""
Write-Host ("-" * 60)
if ($healthy) {
    Write-Host "RESULT: healthy" -ForegroundColor Green
    Write-Host "Dashboard: $base/status"
    Write-Host ""
    exit 0
}
else {
    Write-Host "RESULT: UNHEALTHY - the API is running but a dependency failed" -ForegroundColor Red
    Write-Host "Dashboard: $base/status"
    Write-Host "See docs\MONITORING.md for what each failing check means."
    Write-Host ""
    exit 1
}
