<#
    check_all_reads.ps1 - hits every read-only endpoint and reports what came back.

    Safe: nothing here writes to the database or the filesystem.

    Usage:
        .\check_all_reads.ps1
        .\check_all_reads.ps1 -BaseUrl http://192.168.1.50:5030 -CheckinUID 6
#>
[CmdletBinding()]
param(
    [string]$BaseUrl    = 'http://localhost:5030',
    [string]$CheckinUID = '6'
)

$ErrorActionPreference = 'Continue'

function Write-Result {
    param([string]$Name, [string]$Status, [string]$Detail)
    $colour = 'Green'
    if ($Status -ne 'OK') { $colour = 'Red' }
    Write-Host ("{0,-24} {1,-6} {2}" -f $Name, $Status, $Detail) -ForegroundColor $colour
}

Write-Host "`n=== Monitoring ===" -ForegroundColor Cyan
foreach ($e in 'ping', 'version', 'health', 'metrics', 'routes') {
    try {
        $r = Invoke-RestMethod "$BaseUrl/$e" -TimeoutSec 20
        $detail = ''
        if ($e -eq 'version') { $detail = "v$($r.version) pid $($r.pid)" }
        if ($e -eq 'health')  { $detail = "healthy=$($r.healthy)" }
        if ($e -eq 'routes')  { $detail = "$($r.count) routes" }
        if ($e -eq 'metrics') { $detail = "$($r.totalRequests) requests" }
        if ($e -eq 'ping')    { $detail = "$r" }
        Write-Result $e 'OK' $detail
    } catch {
        Write-Result $e 'FAIL' $_.Exception.Message
    }
}

Write-Host "`n=== Reference lookups ===" -ForegroundColor Cyan
$lookups = 'country', 'emirate', 'room', 'documenttype', 'visitpurpose', 'relationship',
           'paymenttype', 'cardtype', 'checkintype', 'checkouttype', 'escorttype',
           'accessibilitytype', 'cancellationreason', 'dtcmaction'
foreach ($e in $lookups) {
    try {
        $r = Invoke-RestMethod "$BaseUrl/$e" -TimeoutSec 30
        # These endpoints swallow database errors and still answer 200 with {"error": "..."}
        if ($r.PSObject.Properties.Name -contains 'error') {
            Write-Result $e 'FAIL' $r.error
        } else {
            Write-Result $e 'OK' "$(@($r).Count) rows"
        }
    } catch {
        Write-Result $e 'FAIL' $_.Exception.Message
    }
}

Write-Host "`n=== Table dumps ===" -ForegroundColor Cyan
$dumps = 'checkintable', 'guesttable', 'checkinguest', 'guestversion', 'guestattachment',
         'guestdocumentimage', 'payment', 'log', 'checkout', 'guestcheckout',
         'roomchange', 'checkincancellation', 'mainguestchange'
foreach ($e in $dumps) {
    try {
        $r = Invoke-RestMethod "$BaseUrl/$e" -TimeoutSec 60
        if ($r.PSObject.Properties.Name -contains 'error') {
            Write-Result $e 'FAIL' $r.error
        } else {
            Write-Result $e 'OK' "$(@($r).Count) rows"
        }
    } catch {
        Write-Result $e 'FAIL' $_.Exception.Message
    }
}

Write-Host "`n=== GETs that need a JSON body ===" -ForegroundColor Cyan
# PowerShell 5.1 refuses to send a body on GET, so shell out to curl.exe with a file.
$tmp = Join-Path $env:TEMP "idapi_get_body.json"

foreach ($pair in @(@('checkin', 'CheckinStatusRequest'), @('guest', 'GuestStatusRequest'))) {
    $endpoint    = $pair[0]
    $messageType = $pair[1]
    $body = @{
        CheckinUID     = $CheckinUID
        MessageType    = $messageType
        ClientUID      = 'Establishment101'
        MessageUID     = $null
        CorrelationUID = "read-check-$endpoint"
        Timestamp      = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')
    } | ConvertTo-Json
    Set-Content -Path $tmp -Value $body -Encoding utf8

    $raw = curl.exe -s -X GET "$BaseUrl/$endpoint" -H "Content-Type: application/json" --data "@$tmp"
    try {
        $r = $raw | ConvertFrom-Json
        if ($r.hasErrors) {
            Write-Result "GET /$endpoint" 'FAIL' ($r.errorMessages | ConvertTo-Json -Compress)
        } elseif ($endpoint -eq 'guest') {
            Write-Result "GET /$endpoint" 'OK' "$(@($r.guests).Count) guests on checkin $CheckinUID"
        } else {
            Write-Result "GET /$endpoint" 'OK' "room $($r.data.RoomNumber), active=$($r.data.IsActive)"
        }
    } catch {
        Write-Result "GET /$endpoint" 'FAIL' $raw
    }
}

Remove-Item $tmp -ErrorAction SilentlyContinue
Write-Host "`nDone. Nothing was written.`n" -ForegroundColor Cyan
