<#
    make_partner_bundle.ps1 - assemble the zip to send to a partner developer.

    Includes the documentation, the payload collection, the Postman files, the
    runner scripts and a blank config template.

    Deliberately EXCLUDED, because they leak or bloat:
        config.json     database password in plain text, internal host name
        logs\           request logs, may contain guest data
        dist\, build\   38 MB of build output - send the executable separately
        app\            source code; add -IncludeSource if the partner gets it

    Usage:
        .\make_partner_bundle.ps1
        .\make_partner_bundle.ps1 -IncludeSource -OutFile C:\temp\bundle.zip
#>
[CmdletBinding()]
param(
    [string]$OutFile = "",
    [switch]$IncludeSource
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if ($OutFile -eq '') {
    $stamp   = Get-Date -Format 'yyyyMMdd'
    $OutFile = Join-Path $root "ITSthe1.ID-API-partner-bundle-$stamp.zip"
}

$staging = Join-Path $env:TEMP ("idapi_bundle_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $staging -Force | Out-Null

function Copy-Into {
    param([string]$Source, [string]$Relative)
    $target = Join-Path $staging $Relative
    $parent = Split-Path $target -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    Copy-Item $Source $target -Recurse -Force
    Write-Host "  + $Relative" -ForegroundColor DarkGray
}

Write-Host "`nStaging bundle..." -ForegroundColor Cyan

Copy-Into (Join-Path $root 'README.md')             'README.md'
Copy-Into (Join-Path $root 'config.example.json')   'config.example.json'
Copy-Into (Join-Path $root 'requirements.txt')      'requirements.txt'
Copy-Into (Join-Path $root 'check_api.ps1')         'check_api.ps1'
Copy-Into (Join-Path $root 'docs')                  'docs'

if ($IncludeSource) {
    Copy-Into (Join-Path $root 'app')    'app'
    Copy-Into (Join-Path $root 'run.py') 'run.py'
}

# Belt and braces: nothing named config.json, and no logs, ever ship.
Get-ChildItem $staging -Recurse -Force -Include 'config.json', '*.log' |
    ForEach-Object {
        Write-Host "  - removed $($_.Name)" -ForegroundColor Yellow
        Remove-Item $_.FullName -Force
    }

if (Test-Path $OutFile) { Remove-Item $OutFile -Force }
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $OutFile
Remove-Item $staging -Recurse -Force

$size = [math]::Round((Get-Item $OutFile).Length / 1KB, 1)
Write-Host "`nWrote $OutFile ($size KB)" -ForegroundColor Green
Write-Host "Start the partner on docs\PARTNER_HANDOVER.md.`n" -ForegroundColor Cyan
