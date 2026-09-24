<#
    run_write_flow.ps1 - drives the whole business lifecycle end to end:

        POST /checkin            create a stay with one main guest
        GET  /guest              read back the guest ids the other calls need
        POST /guest              add an escort to the open stay
        POST /guestattachment    add a second document to the escort
        POST /roomchange         move the stay to another room
        POST /guestcheckout      check the escort out, stay continues
        POST /checkout           close the stay

    THIS WRITES TO THE DATABASE and saves images under BaseDirectoryPath.
    Every run uses fresh guest codes and document numbers, so it can be
    repeated without tripping "50016 Guest already exist".

    Usage:
        .\run_write_flow.ps1 -Force
        .\run_write_flow.ps1 -Room 003 -NewRoom 004 -Force
        .\run_write_flow.ps1 -CancelInstead -Force    # cancel rather than check out
#>
[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://localhost:5030',
    [string]$Room    = '003',
    [string]$NewRoom = '004',
    [switch]$CancelInstead,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

if (-not $Force) {
    Write-Host "This script writes check-ins, guests, images and check-outs to" -ForegroundColor Yellow
    Write-Host "$BaseUrl (rooms $Room and $NewRoom)." -ForegroundColor Yellow
    $answer = Read-Host "Type YES to continue"
    if ($answer -ne 'YES') { Write-Host "Aborted."; return }
}

# --- run-specific identifiers so repeat runs never collide -------------------
$tag = Get-Date -Format 'MMddHHmmss'
$jpeg = '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q=='

# --- times: every step must be in the past and strictly increasing -----------
$now = Get-Date
function T { param([int]$MinutesAgo) ($now.AddMinutes(-$MinutesAgo)).ToString('yyyy-MM-ddTHH:mm:ss') }
$tCheckin   = T 180
$tEscort    = T 150
$tRoomMove  = T 90
$tGuestOut  = T 60
$tClose     = T 30

function Send-Json {
    param([string]$Method, [string]$Path, $Body)
    $json = $Body | ConvertTo-Json -Depth 10
    try {
        return Invoke-RestMethod -Uri "$BaseUrl$Path" -Method $Method -ContentType 'application/json' -Body $json
    } catch {
        $resp = $_.Exception.Response
        if ($resp) {
            $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
            $text = $reader.ReadToEnd()
            Write-Host "$Method $Path failed:" -ForegroundColor Red
            Write-Host $text -ForegroundColor Red
        } else {
            Write-Host "$Method $Path failed: $($_.Exception.Message)" -ForegroundColor Red
        }
        throw
    }
}

function New-Attachment {
    param([string]$Code, [string]$Name = 'Image_1.jpg')
    return @{
        Id                   = 0
        UID                  = $null
        AttachmentCode       = $Code
        Name                 = $Name
        Size                 = 160
        ContentBase64Encoded = $jpeg
    }
}

# --------------------------------------------------------------------------- 1
Write-Host "`n[1] POST /checkin  (room $Room, $tCheckin)" -ForegroundColor Cyan
$checkinBody = @{
    RoomNumber         = $Room
    IsEarlyCheckin     = $false
    CheckinDateTime    = $tCheckin
    PaymentMethodCode  = 'cash'
    CreditCardNumber   = $null
    CreditCardTypeCode = $null
    PaidAmount         = 0
    Comment            = "write flow $tag"
    IsWaitingForRoom   = $false
    IsHouseUse         = $false          # must be present and false, see PAYLOADS.md
    MessageType        = 'CheckinRequest'
    ClientUID          = 'Establishment101'
    MessageUID         = $null
    CorrelationUID     = "flow-$tag-checkin"
    Timestamp          = $tCheckin
    Guests             = @(
        @{
            UID                   = $null
            GuestCode             = "WF$tag" + "MAIN"
            FirstName             = 'John'
            LastName              = 'Smith'
            ArabicName            = 'جون سميث'
            GenderCode            = 'male'
            Email                 = 'john.smith@example.com'
            Mobile                = '501234567'
            ResidenceCountryPhone = '971501234567'
            BirthDate             = '1985-06-14T00:00:00'
            BirthPlace            = 'London'
            NationalityCode       = 'GB'
            ResidenceCountryCode  = 'AE'
            RelationshipCode      = $null
            VisitPurposeCode      = 'tourism'
            CheckinDateTime       = $tCheckin
            CheckoutDateTime      = $null
            IsMainGuest           = $true
            AttachmentTypeCode    = 'passport'
            DocumentNumber        = "WF$tag" + "M"
            IssueCountryCode      = 'GB'
            IssueDate             = '2020-01-15T00:00:00'
            ExpiryDate            = '2030-01-15T00:00:00'
            EmirateCode           = $null
            RequiresAccessibility = $false
            AccessibilityTypes    = @()
            OtherAccessibilityType = ''
            Attachments           = @( (New-Attachment "WF$tag-DOC-M") )
        }
    )
}
$r1 = Send-Json 'POST' '/checkin' $checkinBody
$checkinUID = $r1.CheckinUID
Write-Host "    CheckinUID = $checkinUID" -ForegroundColor Green

# --------------------------------------------------------------------------- 2
Write-Host "`n[2] POST /guest  (add escort, $tEscort)" -ForegroundColor Cyan
$escortBody = @{
    CheckinUID     = "$checkinUID"
    Comment        = "write flow $tag escort"
    MessageType    = 'GuestRequest'
    ClientUID      = 'Establishment101'
    MessageUID     = $null
    CorrelationUID = "flow-$tag-escort"
    Timestamp      = $tEscort
    GuestInfo      = @{
        UID                   = $null
        GuestCode             = "WF$tag" + "ESC"
        FirstName             = 'Alan'
        LastName              = 'Turing'
        ArabicName            = 'آلان تورينج'
        GenderCode            = 'male'
        Email                 = 'alan.turing@example.com'
        Mobile                = '501550001'
        ResidenceCountryPhone = '971501550001'
        BirthDate             = '1990-11-20T00:00:00'
        BirthPlace            = 'Manchester'
        NationalityCode       = 'GB'
        ResidenceCountryCode  = 'AE'
        RelationshipCode      = 'friend'        # required: escorts are never main guests
        VisitPurposeCode      = 'visitor'
        CheckinDateTime       = $tEscort
        CheckoutDateTime      = $null
        IsMainGuest           = $false
        AttachmentTypeCode    = 'passport'
        DocumentNumber        = "WF$tag" + "E"
        IssueCountryCode      = 'GB'
        IssueDate             = '2019-05-01T00:00:00'
        ExpiryDate            = '2029-05-01T00:00:00'
        EmirateCode           = $null
        RequiresAccessibility = $false
        AccessibilityTypes    = @()
        OtherAccessibilityType = ''
        Attachments           = @( (New-Attachment "WF$tag-DOC-E") )
    }
}
$r2 = Send-Json 'POST' '/guest' $escortBody
Write-Host "    escort added, response uid = $($r2.guests[0].uid)" -ForegroundColor Green

# --------------------------------------------------------------------------- 3
Write-Host "`n[3] GET /guest  (read the real guest ids)" -ForegroundColor Cyan
$tmp = Join-Path $env:TEMP "idapi_flow_get.json"
$getBody = @{
    CheckinUID     = "$checkinUID"
    MessageType    = 'GuestStatusRequest'
    ClientUID      = 'Establishment101'
    MessageUID     = $null
    CorrelationUID = "flow-$tag-getguest"
    Timestamp      = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')
} | ConvertTo-Json
Set-Content -Path $tmp -Value $getBody -Encoding utf8
$r3 = (curl.exe -s -X GET "$BaseUrl/guest" -H "Content-Type: application/json" --data "@$tmp") | ConvertFrom-Json
Remove-Item $tmp -ErrorAction SilentlyContinue

$mainGuest   = $r3.guests | Where-Object { $_.isMainGuest } | Select-Object -Last 1
$escortGuest = $r3.guests | Where-Object { -not $_.isMainGuest } | Select-Object -Last 1
Write-Host "    main guest uid   = $($mainGuest.uid)"   -ForegroundColor Green
Write-Host "    escort guest uid = $($escortGuest.uid)" -ForegroundColor Green

# --------------------------------------------------------------------------- 4
Write-Host "`n[4] POST /guestattachment  (extra document for the escort)" -ForegroundColor Cyan
$attachBody = @{
    CheckinUID     = "$checkinUID"
    GuestUID       = "$($escortGuest.uid)"
    MessageType    = 'GuestAttachmentRequest'
    ClientUID      = 'Establishment101'
    MessageUID     = $null
    CorrelationUID = "flow-$tag-attach"
    Timestamp      = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')
    Attachments    = @( (New-Attachment "WF$tag-DOC-EXTRA" 'Image_2.jpg') )
}
$r4 = Send-Json 'POST' '/guestattachment' $attachBody
Write-Host "    attachments now on file: $(@($r4.guests[0].attachments).Count)" -ForegroundColor Green

# --------------------------------------------------------------------------- 5
Write-Host "`n[5] POST /roomchange  ($Room -> $NewRoom, $tRoomMove)" -ForegroundColor Cyan
$moveBody = @{
    CheckinUID     = "$checkinUID"
    NewRoomNumber  = $NewRoom
    EffectiveDate  = $tRoomMove
    Comment        = "write flow $tag move"
    MessageType    = 'RoomChangeRequest'
    ClientUID      = 'Establishment101'
    MessageUID     = $null
    CorrelationUID = "flow-$tag-move"
    Timestamp      = $tRoomMove
}
$r5 = Send-Json 'POST' '/roomchange' $moveBody
Write-Host "    moved, CheckinUID = $($r5.CheckinUID)" -ForegroundColor Green

# --------------------------------------------------------------------------- 6
Write-Host "`n[6] POST /guestcheckout  (escort leaves, $tGuestOut)" -ForegroundColor Cyan
$guestOutBody = @{
    CheckinUID       = "$checkinUID"
    GuestUID         = "$($escortGuest.uid)"
    CheckoutDateTime = $tGuestOut
    NewMainGuestUID  = $null           # only needed when the MAIN guest is leaving
    MessageType      = 'GuestCheckoutRequest'
    ClientUID        = 'Establishment101'
    MessageUID       = $null
    CorrelationUID   = "flow-$tag-guestout"
    Timestamp        = $tGuestOut
}
$r6 = Send-Json 'POST' '/guestcheckout' $guestOutBody
Write-Host "    escort checked out of CheckinUID $($r6.CheckinUID)" -ForegroundColor Green

# --------------------------------------------------------------------------- 7
if ($CancelInstead) {
    Write-Host "`n[7] POST /checkincancellation  ($tClose)" -ForegroundColor Cyan
    $closeBody = @{
        CheckinUID             = "$checkinUID"
        CancellationDateTime   = $tClose
        CancellationReasonCode = 'UserError'
        Comment                = "write flow $tag cancel"
        MessageType            = 'CheckinCancellationRequest'
        ClientUID              = 'Establishment101'
        MessageUID             = $null
        CorrelationUID         = "flow-$tag-cancel"
        Timestamp              = $tClose
    }
    $r7 = Send-Json 'POST' '/checkincancellation' $closeBody
    Write-Host "    cancelled CheckinUID $($r7.CheckinUID)" -ForegroundColor Green
} else {
    Write-Host "`n[7] POST /checkout  ($tClose)" -ForegroundColor Cyan
    $closeBody = @{
        CheckinUID       = "$checkinUID"
        IsLateCheckout   = $false
        CheckoutDateTime = $tClose
        Comment          = "write flow $tag close"
        MessageType      = 'CheckoutRequest'
        ClientUID        = 'Establishment101'
        MessageUID       = $null
        CorrelationUID   = "flow-$tag-close"
        Timestamp        = $tClose
    }
    $r7 = Send-Json 'POST' '/checkout' $closeBody
    Write-Host "    closed CheckinUID $($r7.CheckinUID)" -ForegroundColor Green
}

Write-Host "`nFlow complete. CheckinUID $checkinUID, room $NewRoom released.`n" -ForegroundColor Cyan
