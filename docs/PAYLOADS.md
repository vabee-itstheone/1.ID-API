# Payload reference — exercising every endpoint

Companion to [API.md](API.md). Where API.md describes the contract, this file
gives **payloads you can send right now**, using code values and record IDs that
exist in the database this instance points at.

Every payload here also exists as a ready-to-send file in
[`docs/payloads/`](payloads/), plus two runner scripts.

Base URL: `http://localhost:5030`

> Verified against the reference instance (SQL Server 2022), database `itsthe1.id`,
> schema `[itsthe1.id].[itsthe1.id]`, API v1.0.0, on **2026-08-04**.
> The *codes* are stable; the *row IDs* are not — refresh
> [Current database state](#current-database-state) after repointing
> `SQLALCHEMY_DATABASE_URI`.

---

## Contents

- [Read this first: writes are broken on this database](#read-this-first-writes-are-broken-on-this-database)
- [The files](#the-files)
- [How to send a request](#how-to-send-a-request)
- [The envelope](#the-envelope)
- [The guest object](#the-guest-object)
- [Valid code values](#valid-code-values)
- [Current database state](#current-database-state)
- [Endpoint catalogue](#endpoint-catalogue)
- [Reference lookups (GET)](#reference-lookups-get)
- [Check-in](#check-in)
- [Escorts and additional guests](#escorts-and-additional-guests)
- [Guest attachments](#guest-attachments)
- [Guest check-out and main-guest handover](#guest-check-out-and-main-guest-handover)
- [Room change](#room-change)
- [Check-out](#check-out)
- [Check-in cancellation](#check-in-cancellation)
- [Monitoring](#monitoring)
- [Suggested test order](#suggested-test-order)
- [Error codes](#error-codes)
- [Gotchas](#gotchas)
- [What has been verified](#what-has-been-verified)

---

## Read this first: writes are broken on this database

Every endpoint that stores a document image — `POST /checkin`,
`POST /checkin/AddBackdatedCheckin`, `POST /guest`, `PUT /guest`,
`POST /guestattachment` — writes to the `GuestDocumentImage` model, and **that
table does not exist in this database**:

```
42S02 Invalid object name 'itsthe1.id.itsthe1.id.guestdocumentimages'
```

The model is at [../app/models.py:274](../app/models.py#L274). `GET /guestdocumentimage`
surfaces the same error (as HTTP 200 with an `{"error": …}` body — see
[Gotchas](#gotchas)).

**What it looks like when it bites.** `POST /checkin` answers **500**, and
because the handler commits in stages rather than in one transaction, it leaves
behind an orphan `checkin` row, an orphan `payment` row and a `guest` row, with
no `checkinguest`, no `guestversion` and no room flag. Check-ins **14, 15 and 16**
in the snapshot below are exactly that: three failed attempts on room `002` from
2026-08-03, visible in `logs/api.log`:

```
2026-08-03 15:25:24 WARNING POST /checkin -> 500 (1595 ms) from 127.0.0.1
2026-08-03 15:26:58 WARNING POST /checkin -> 500 (1269 ms) from 127.0.0.1
2026-08-03 15:29:20 WARNING POST /checkin -> 500 (1317 ms) from 127.0.0.1
```

So: the payloads below are correct, but the write half of the collection will
fail on this database until the table is created. Either create it —

```sql
USE [itsthe1.id];
CREATE TABLE [itsthe1.id].[guestdocumentimages] (
    DocumentId     INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    GuestId        INT NOT NULL REFERENCES [itsthe1.id].[guest](Id),
    DocumentUID    NVARCHAR(255) NULL,
    AttachmentCode NVARCHAR(255) NULL,
    [FileName]     NVARCHAR(255) NULL,
    FileSizeKB     INT NULL,
    ImageData      VARBINARY(MAX) NULL,
    UploadedAt     DATETIME2 NOT NULL CONSTRAINT DF_guestdocumentimages_UploadedAt DEFAULT SYSDATETIME()
);
```

— or point the model at whatever the table is really called. Clean up the
orphans afterwards:

```sql
DELETE c FROM [itsthe1.id].[checkin] c
 WHERE c.Id IN (14, 15, 16)
   AND NOT EXISTS (SELECT 1 FROM [itsthe1.id].[checkinguest] g WHERE g.CheckinId = c.Id);
DELETE FROM [itsthe1.id].[payment] WHERE Id IN (14, 15, 16);
```

Read-only endpoints are unaffected — all 26 working lookups were run on
2026-08-04 and are green.

---

## The files

| File | Endpoint | Notes |
|---|---|---|
| [`01_checkin_get.json`](payloads/01_checkin_get.json) | `GET /checkin` | body-on-GET |
| [`02_checkin_post_cash.json`](payloads/02_checkin_post_cash.json) | `POST /checkin` | one main guest, cash |
| [`03_checkin_post_with_escorts.json`](payloads/03_checkin_post_with_escorts.json) | `POST /checkin` | **main guest + two escorts** |
| [`04_checkin_post_creditcard.json`](payloads/04_checkin_post_creditcard.json) | `POST /checkin` | credit card, early check-in, accessibility `other` |
| [`05_checkin_post_houseuse.json`](payloads/05_checkin_post_houseuse.json) | `POST /checkin` | house use, no payment |
| [`06_checkin_put.json`](payloads/06_checkin_put.json) | `PUT /checkin` | amend an open stay |
| [`07_checkin_post_backdated.json`](payloads/07_checkin_post_backdated.json) | `POST /checkin/AddBackdatedCheckin` | stay already ended |
| [`08_guest_get.json`](payloads/08_guest_get.json) | `GET /guest` | body-on-GET |
| [`09_guest_post_add_escort.json`](payloads/09_guest_post_add_escort.json) | `POST /guest` | **add an escort to an open stay** |
| [`10_guest_put_edit_escort.json`](payloads/10_guest_put_edit_escort.json) | `PUT /guest` | edit that escort |
| [`11_guestattachment_post.json`](payloads/11_guestattachment_post.json) | `POST /guestattachment` | extra document |
| [`12_guestcheckout_post_escort.json`](payloads/12_guestcheckout_post_escort.json) | `POST /guestcheckout` | escort leaves |
| [`13_guestcheckout_post_mainguest_handover.json`](payloads/13_guestcheckout_post_mainguest_handover.json) | `POST /guestcheckout` | **main guest leaves, escort takes over** |
| [`14_roomchange_post.json`](payloads/14_roomchange_post.json) | `POST /roomchange` | |
| [`15_checkout_post.json`](payloads/15_checkout_post.json) | `POST /checkout` | |
| [`16_checkout_put.json`](payloads/16_checkout_put.json) | `PUT /checkout` | amend a closed stay |
| [`17_checkincancellation_post.json`](payloads/17_checkincancellation_post.json) | `POST /checkincancellation` | |

Anything reading `REPLACE_WITH_…` needs an id from an earlier response.

### Postman

[`ITSthe1.ID.postman_collection.json`](payloads/ITSthe1.ID.postman_collection.json)
and [`ITSthe1.ID.postman_environment.json`](payloads/ITSthe1.ID.postman_environment.json)
— **61 requests in 8 folders**, generated from the files above. Every endpoint,
with assertions on each request and test scripts that capture ids as you go:

| Variable | Set by | Used by |
|---|---|---|
| `checkinUID` | any `POST /checkin` | everything downstream |
| `guestUID` | `POST /guest`, `GET /guest` | attachment, guest check-out |
| `mainGuestUID` | `GET /guest` | handover — the departing guest |
| `newMainGuestUID` | `POST /guest`, `GET /guest` | handover — the successor |

So the `REPLACE_WITH_…` tokens are already resolved to `{{variables}}` there —
run the folders in order and no id needs pasting by hand. Postman also sends a
body on a GET, which PowerShell cannot.

The lookup and dump folders assert that the body is an **array**, not just that
the call returned 200 — see the `{"error": …}`-with-200 gotcha below.

### Two runners

```bash
docs\payloads\check_all_reads.ps1
```

Hits every read-only endpoint (monitoring, 14 lookups, 13 table dumps, both
body-on-GET endpoints) and prints OK/FAIL per endpoint. Writes nothing.

```bash
docs\payloads\run_write_flow.ps1 -Force
```

Drives the whole lifecycle — check-in → add escort → attachment → room change →
guest check-out → check-out — generating fresh guest codes and document numbers
each run so it can be repeated. **This writes to the database**, and will fail at
step 1 until the `guestdocumentimages` table exists.

---

## How to send a request

### Two endpoints need a JSON body on a GET

`GET /checkin` and `GET /guest` take their identifier in the **request body**,
not the query string. PowerShell 5.1 refuses outright:

```powershell
Invoke-RestMethod -Uri http://localhost:5030/checkin -Method Get -Body $json
# Cannot send a content-body with this verb-type.
```

Use `curl.exe` with the payload in a file:

```bash
curl.exe -s -X GET http://localhost:5030/checkin -H "Content-Type: application/json" --data "@docs/payloads/01_checkin_get.json"
```

### Always put JSON in a file

Passing a JSON string inline to `curl.exe` from PowerShell strips the double
quotes, and the API answers:

```json
{"errorMessages":{"general":"The browser (or proxy) sent a request that this server could not understand."},"status":400}
```

That message means *malformed JSON*, not a validation failure.

For POST/PUT, `Invoke-RestMethod` is fine:

```powershell
Invoke-RestMethod -Uri http://localhost:5030/checkin -Method Post -ContentType "application/json" -Body (Get-Content .\docs\payloads\02_checkin_post_cash.json -Raw)
```

---

## The envelope

Every business request carries these five fields alongside its own payload:

```json
{
  "MessageType": "CheckinRequest",
  "ClientUID": "Establishment101",
  "MessageUID": null,
  "CorrelationUID": "test-001",
  "Timestamp": "2026-08-04T08:00:00"
}
```

| Field | Notes |
|---|---|
| `MessageType` | Free text. Echoed back; never validated. |
| `ClientUID` | **Not validated** — any string works. Error 40001 exists in the code table but this build cannot raise it. |
| `MessageUID` | Send `null`; the API generates one. |
| `CorrelationUID` | Your id, echoed back unchanged. Use it to pair request and response. |
| `Timestamp` | ISO 8601. Not validated. |

Success carries `hasErrors: false`. Validation failures return **400** with
`hasErrors: true` and a numbered code in `errorMessages.general`, e.g.
`40002 Checkin room does not exist`.

Note that the three simplest write endpoints — `POST /checkout`,
`POST /roomchange`, `POST /checkincancellation` — return a **bare**
`{"CheckinUID": …}` on success, not the envelope. Only their *errors* use it.

---

## The guest object

The same shape is used in three places: `Guests[]` on `POST`/`PUT /checkin` and
on `AddBackdatedCheckin`, and `GuestInfo` on `POST`/`PUT /guest`.

| Field | Required | Rule |
|---|---|---|
| `GuestCode` | yes | string, ≤ 75 chars. Your identifier for the guest on this stay. |
| `FirstName` | yes | **English letters and spaces only**, no double spaces. |
| `LastName` | yes | same, ≤ 45 chars on `PUT /checkin`. |
| `ArabicName` | **yes on the `Guests[]` endpoints** | **Arabic characters and spaces only.** Omitting it fails validation — see [Gotchas](#gotchas). Never stored: the API transliterates `FirstName`/`LastName` instead. |
| `GenderCode` | yes | `male` or `female`. Stored capitalised. |
| `Email` | key must be present | may be `null`; if given, must contain `@`. |
| `Mobile` | yes | **digits only**, no `+` and no spaces. |
| `ResidenceCountryPhone` | key must be present | free text. |
| `BirthDate` | yes | ISO, not in the future. |
| `BirthPlace` | yes | **letters only, no spaces** (`Abu Dhabi` fails, `AbuDhabi` passes). |
| `NationalityCode` | yes | ISO two-letter, must exist in `country.TwoCode`. |
| `ResidenceCountryCode` | yes | ISO two-letter. Also determines the stored `MobileCode`. |
| `RelationshipCode` | **only for non-main guests** | must exist in `relationship.DtcmCode`. Send `null` for the main guest. |
| `VisitPurposeCode` | yes | must exist in `visitpurpose.DtcmCode`. |
| `CheckinDateTime` | yes | ≥ the transaction's `CheckinDateTime`, not in the future. |
| `CheckoutDateTime` | key must be present | `null` except on `AddBackdatedCheckin`. |
| `IsMainGuest` | yes | exactly one `true` per `POST /checkin`. |
| `AttachmentTypeCode` | yes | must exist in `documenttype.DtcmCode`. |
| `DocumentNumber` | yes | **alphanumeric only, no spaces.** This is the guest's identity — see [Gotchas](#gotchas). |
| `IssueCountryCode` | yes | ISO two-letter. |
| `IssueDate` | yes | not in the future, strictly before `ExpiryDate`. |
| `ExpiryDate` | yes | must not be in the past. |
| `EmirateCode` | **required when `IssueCountryCode` is `AE`** | must exist in `emirate.DtcmCode`. |
| `RequiresAccessibility` | no | `true` stores the accessibility JSON, `false`/absent stores `null`. |
| `AccessibilityTypes` | no | `[{"Code": "mobility"}, …]`. |
| `OtherAccessibilityType` | **required when the list contains `other`** | free text. |
| `Attachments` | yes, at least one | see below. |
| `UID` | no | send `null`; ignored on create. |

An attachment:

```json
{
  "Id": 0,
  "UID": null,
  "AttachmentCode": "PC-DOC-0001",
  "Name": "Image_1.jpg",
  "Size": 160,
  "ContentBase64Encoded": "<base64 JPEG, decoded size under 200 KB>"
}
```

`Name` becomes the filename on disk under `BaseDirectoryPath` — the API does not
rename it on `POST /checkin`/`POST /guest`, so a guest's second document needs a
distinct name (`POST /guestattachment` *does* auto-suffix collisions to
`Image_2_1.jpg`). Images are resized to 1080×720 and re-encoded at quality 85.

A valid 1×1 JPEG for testing, used by every payload in this collection:

```
/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a
HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA
AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q==
```

---

## Valid code values

Live contents of the reference tables, read 2026-08-04. Countries match on
**`TwoCode`**; everything else on **`DtcmCode`**.

**`PaymentMethodCode`** — `cash`, `creditcard`

**`CreditCardTypeCode`** — only when `PaymentMethodCode` is `creditcard`

| Code | Card | Number length |
|---|---|---|
| `visa` | Visa | 13–16 |
| `mastercard` | MasterCard | 16 |
| `amex` | American Express | 15 |
| `diners` | Diners Club | 14–16 |

> Visa Electron exists but its `DtcmCode` is the string `"0"` — almost certainly a
> data bug. Avoid it in tests.

**`AttachmentTypeCode`** (21 values)

`passport` · `emiratesid` · `uaedrivinglicence` · `identificationcardgcc` ·
`diplomaticpassport` · `privatepassport` · `temporarypassport` ·
`servicepassport` · `politicalpassport` · `seamanpassport` · `unpassport` ·
`traveldocument` · `lebanesetraveldocument` · `iraqitraveldocument` ·
`syriantraveldocument` · `egyptiantraveldocument` · `generaldeclarationform` ·
`labourcarduae` · `diplomaticcard` · `airlineid` · `militarycard`

**`VisitPurposeCode`** — `tourism` · `visitor` · `business` · `medical` ·
`religious` · `Athlete` · `crewmember` · `hotelstaff` · `medicalstaff` ·
`otherstaff` · `patients`

> `Athlete` is capitalised in the table — send it exactly as shown. `tourism`
> appears on eight rows (Ids 1, 8–14); the lookup takes the first, Id 1.

**`RelationshipCode`** — `businessAssociate` · `familyHelper` · `familyMember` ·
`friend` · `visitor` — required for **non-main** guests only.

**`EmirateCode`** — `dubai` · `abudhabi` · `sharjah` · `fujirah` · `rak` ·
`ajman` · `ummalquwain` · `alain` · `westernareas` — required only when
`IssueCountryCode` is `AE`.

**`AccessibilityTypes[].Code`** — `hearing` · `visual` · `mobility` · `other`

**`CancellationReasonCode`** — `Unhappy` (Unsatisfied Guest) · `UserError` (User Error)

**`GenderCode`** — `male` · `female`

**Escort types** (`GET /escorttype`) — `1 ChildEscort`, `2 AdultEscort`. **No
payload field selects one** — see [Escorts](#escorts-and-additional-guests).

**Country codes** — ISO two-letter, 252 rows: `AE`, `GB`, `US`, `IN`, `LK`, `DE`,
`FR` … full list from `GET /country`.

---

## Current database state

Snapshot 2026-08-04.

**Rooms** — 31 total, 2 occupied: `001` (check-in 6) and `006` (check-in 8).
Free: `002` `003` `004` `005` `007` `008` `009` `010` `011` `012` `013` `014` …

**Check-ins**

| Id | Room | Check-in | Active | Note |
|---|---|---|---|---|
| 6 | 001 | 2026-05-18 13:52 | **yes** | main guest 3 |
| 7 | 012 | 2026-05-18 14:27 | no | has the only escort row in the database |
| 8 | 006 | 2026-05-19 13:14 | **yes** | main guest 4 |
| 9–13 | 006, 010, 013, 003, 009 | May–Jul | no | closed |
| 14, 15, 16 | 002 | 2026-08-03 09:00 | yes | **orphans from failed POSTs** — no guests, room not flagged |

Only check-ins **6** and **8** are genuinely open — the only valid targets for
check-out, room change, add-guest and cancellation.

**Guests**

| Id | Name | Document | Nationality |
|---|---|---|---|
| 3 | Jeremy Daniel Alexander | 118812378 | 202 |
| 4 | Anthony Kishan Fernando Pulle | 784196491047393 | 74 |
| 5 | Jeremy Daniel Alexander | 784198947370577 | 202 |
| 6 | John Smith | GB9876543 | 84 |

Refresh the snapshot:

```sql
SELECT Id, RoomNumber, IsChecked, CheckinId FROM [itsthe1.id].[room] WHERE IsChecked = 1;
SELECT Id, RoomNumber, CheckinDate, IsActive FROM [itsthe1.id].[checkin] ORDER BY Id;
SELECT Id, CheckinId, GuestId, IsMainGuest, EscortTypeId, CheckoutDate FROM [itsthe1.id].[checkinguest] ORDER BY Id;
```

---

## Endpoint catalogue

50 routes, from `GET /routes`.

| Group | Routes |
|---|---|
| Check-in | `GET POST PUT /checkin`, `POST /checkin/AddBackdatedCheckin`, `GET /checkintable` |
| Guest | `GET POST PUT /guest`, `GET /guesttable` |
| Guest documents | `GET POST /guestattachment`, `GET /guestdocumentimage` |
| Departure | `GET POST PUT /checkout`, `GET POST /guestcheckout`, `GET POST /checkincancellation` |
| Movement | `GET POST /roomchange`, `GET /mainguestchange` |
| Lookups | `/country /emirate /room /documenttype /visitpurpose /relationship /paymenttype /cardtype /checkintype /checkouttype /escorttype /accessibilitytype /cancellationreason /dtcmaction` |
| Audit dumps | `/checkinguest /guestversion /payment /log` |
| Monitoring | `/ /ping /version /health /metrics`, `POST /metrics/reset`, `/routes /status /favicon.ico` |

---

## Reference lookups (GET)

No body, no parameters; each returns the whole table as a JSON array.

Verified 2026-08-04 — 26 of 27 return data:

| | |
|---|---|
| `country` 252 · `documenttype` 21 · `visitpurpose` 18 · `dtcmaction` 18 · `roomchange` 13 · `checkintable` 11 | `payment` 11 · `emirate` 9 · `checkinguest` 9 · `guestversion` 9 · `guestcheckout` 9 · `checkout` 6 |
| `relationship` 5 · `cardtype` 5 · `accessibilitytype` 4 · `guesttable` 4 · `guestattachment` 3 · `room` 31 · `log` 28 | `paymenttype` 2 · `checkintype` 2 · `checkouttype` 2 · `escorttype` 2 · `cancellationreason` 2 · `checkincancellation` 1 · `mainguestchange` 0 |

`GET /guestdocumentimage` fails — see [the warning at the top](#read-this-first-writes-are-broken-on-this-database).

> **A 200 from a lookup is not proof of success.** These endpoints catch their own
> database errors and return `{"error": "…"}` with status 200. Inspect the body —
> `check_all_reads.ps1` does.

---

## Check-in

### `GET /checkin` — fetch one

Body required. [`01_checkin_get.json`](payloads/01_checkin_get.json)

```json
{
  "CheckinUID": "6",
  "MessageType": "CheckinStatusRequest",
  "ClientUID": "Establishment101",
  "MessageUID": null,
  "CorrelationUID": "test-checkin-get-001",
  "Timestamp": "2026-08-04T08:00:00"
}
```

Verified response:

```json
{
  "hasErrors": false,
  "messageType": "CheckinRequest",
  "clientUID": "Establishment101",
  "correlationUID": "test-checkin-get-001",
  "data": {
    "Id": 6, "CheckinUID": null, "RoomNumber": "001",
    "CheckinDate": "2026-05-18T13:52:55", "IsActive": true,
    "ChargeExtra": false, "IsFeeUpdated": false, "TDFee": null,
    "AddedAt": "2026-05-18T13:52:55", "AddedFrom": "FRONTDESK-PC",
    "CheckinTypeId": 1, "PaymentId": 6,
    "ChildEscortCount": null, "AdultEscortCount": null
  }
}
```

All 14 fields match the 1.ID specification's § 1.1.3 response exactly.

Unknown `CheckinUID` → **404** `"Check-in not found"`.

### `POST /checkin` — create

The big one: creates the payment, the check-in, each guest, their documents,
their `checkinguest` rows, a log row and a `guestversion` row per guest, then
flags the room. [`02_checkin_post_cash.json`](payloads/02_checkin_post_cash.json)

```json
{
  "RoomNumber": "003",
  "IsEarlyCheckin": false,
  "CheckinDateTime": "2026-08-04T08:00:00",
  "PaymentMethodCode": "cash",
  "CreditCardNumber": null,
  "CreditCardTypeCode": null,
  "PaidAmount": 0,
  "Comment": "payload collection - simple cash checkin",
  "IsWaitingForRoom": false,
  "IsHouseUse": false,
  "MessageType": "CheckinRequest",
  "ClientUID": "Establishment101",
  "MessageUID": null,
  "CorrelationUID": "test-checkin-cash-001",
  "Timestamp": "2026-08-04T08:00:00",
  "Guests": [ { …one guest object, IsMainGuest true… } ]
}
```

Transaction-level rules:

| Rule | Code if broken |
|---|---|
| `RoomNumber` must exist | 40002 |
| Room must be active, and not already occupied | 40003 / 40050 |
| Check-in must not overlap the room's previous stay | free-text message |
| `CheckinDateTime` must not be in the future | 40004 |
| At least one guest | 40005 |
| Exactly one `IsMainGuest: true` | 40006 / 40028 |
| At least one guest whose `CheckinDateTime` equals the transaction's | 40033 |
| `PaymentMethodCode` must be `cash` or `creditcard` | 40007 |
| `CreditCardNumber` required with `creditcard` | 40008 |
| **`IsHouseUse` must be present** — house use rejects payment method, card, early check-in and waiting-for-room | 40035 / 40036 / 40037 / 40038 |

Success returns the envelope plus:

```json
{
  "CheckinUID": 17,
  "guests": [ { "uid": 13, "guestCode": "PC-MAIN-0001", "attachments": [ { "uid": 5, "attachmenttCode": "PC-DOC-MAIN-0001" } ] } ],
  "requestMessageID": 29,
  "hasErrors": false
}
```

**Capture `CheckinUID`** — everything downstream needs it. Note `guests[].uid`
here is the **`checkinguest` id**, not the guest id; the other endpoints want
the guest id, which you get from `GET /guest`. See [Gotchas](#gotchas).

Variants: [`04_checkin_post_creditcard.json`](payloads/04_checkin_post_creditcard.json)
(card + early check-in + accessibility `other`),
[`05_checkin_post_houseuse.json`](payloads/05_checkin_post_houseuse.json)
(`IsHouseUse: true`, every payment field `null`).

### `PUT /checkin` — amend an open stay

[`06_checkin_put.json`](payloads/06_checkin_put.json)

The identifier is **`UID`**, not `CheckinUID`. `Guests[]` must carry the *full*
guest objects, exactly one with `IsMainGuest: true`, and `CheckoutDateTime` must
stay `null` — sending one is rejected with 40023.

`CheckinDateTime` cannot move earlier than the stay's current check-in time
(overlap check), and each guest's own `CheckinDateTime` must be ≥ it (50014) and
not in the future (50015). 40011 if the stay is already checked out.

> This handler finds the row to update with
> `CheckinGuest.query.filter(GuestId == guest.Id).order_by(Id.desc()).first()` —
> the guest's **latest row across every check-in**, not the row on this
> check-in ([routes.py:2134](../app/checkin/routes.py#L2134)). If the same person is
> on a newer stay, the wrong row is edited. Keep test guests unique per stay.

### `POST /checkin/AddBackdatedCheckin`

[`07_checkin_post_backdated.json`](payloads/07_checkin_post_backdated.json)

Same payload as `POST /checkin` plus **`CheckoutDateTime` at both levels** — the
transaction and every guest. Records a stay that has already started and ended,
so the normal overlap rules are relaxed (`BackdatedCheckinAction`), but:

- `CheckoutDateTime` is required (40014) and must be after `CheckinDateTime` (40034)
- neither may be in the future (40004)
- every guest's window must sit inside the transaction's (40035)
- the room's existing history must not overlap the requested window

### `GET /checkintable`

No body. Dumps every check-in row. Diagnostic helper, not part of the 1.ID spec.

---

## Escorts and additional guests

"Escort" is this API's word for anyone on the stay who is not the main guest:
family, friends, business associates. They live in `checkinguest` alongside the
main guest, distinguished by `IsMainGuest = false`, a `RelationshipName`, and an
`EscortTypeId`.

There are **two ways to add one**, and they use different endpoints.

### 1. At check-in — extra entries in `Guests[]`

[`03_checkin_post_with_escorts.json`](payloads/03_checkin_post_with_escorts.json)
sends one main guest and two escorts in a single `POST /checkin`. Each escort is
an ordinary guest object with:

```json
{
  "GuestCode": "PC-ESCORT-0101",
  "IsMainGuest": false,
  "RelationshipCode": "familyMember",
  "CheckinDateTime": "2026-08-04T08:05:00",
  "…": "all the usual guest fields and at least one attachment"
}
```

Rules specific to escorts in this payload:

- `RelationshipCode` is **required** and must exist in `relationship.DtcmCode`, or 50009
- an escort's `CheckinDateTime` may be later than the transaction's, never earlier (50014)
- at least one guest — normally the main guest — must match the transaction's `CheckinDateTime` exactly (40033)
- exactly one `IsMainGuest: true` in the whole array (40006 / 40028)

### 2. After check-in — `POST /guest`

[`09_guest_post_add_escort.json`](payloads/09_guest_post_add_escort.json). This is
the "add escort" button in the WPF client.

```json
{
  "CheckinUID": "17",
  "Comment": "add an escort to an open checkin",
  "MessageType": "GuestRequest",
  "ClientUID": "Establishment101",
  "MessageUID": null,
  "CorrelationUID": "test-add-escort-001",
  "Timestamp": "2026-08-04T08:30:00",
  "GuestInfo": {
    "GuestCode": "PC-ESCORT-0500",
    "FirstName": "Alan",
    "LastName": "Turing",
    "ArabicName": "آلان تورينج",
    "GenderCode": "male",
    "Email": "alan.turing@example.com",
    "Mobile": "501550001",
    "ResidenceCountryPhone": "971501550001",
    "BirthDate": "1990-11-20T00:00:00",
    "BirthPlace": "Manchester",
    "NationalityCode": "GB",
    "ResidenceCountryCode": "AE",
    "RelationshipCode": "friend",
    "VisitPurposeCode": "visitor",
    "CheckinDateTime": "2026-08-04T08:30:00",
    "CheckoutDateTime": null,
    "IsMainGuest": false,
    "AttachmentTypeCode": "passport",
    "DocumentNumber": "GB1122334",
    "IssueCountryCode": "GB",
    "IssueDate": "2019-05-01T00:00:00",
    "ExpiryDate": "2029-05-01T00:00:00",
    "EmirateCode": null,
    "RequiresAccessibility": false,
    "AccessibilityTypes": [],
    "OtherAccessibilityType": "",
    "Attachments": [ { "Id": 0, "UID": null, "AttachmentCode": "PC-DOC-0500", "Name": "Image_1.jpg", "Size": 160, "ContentBase64Encoded": "…" } ]
  }
}
```

One guest per request — `GuestInfo` is an object, not an array. Rules:

| Rule | Code |
|---|---|
| `CheckinUID` present, stay still open | 40009 / 40011 |
| `GuestInfo` present | 50010 |
| `IsMainGuest: false` with a valid `RelationshipCode` | 50009 |
| Escort's `CheckinDateTime` ≥ the stay's check-in | 50014 |
| …and not in the future | 50015 |
| That document number is not already on this stay | **50016** |
| At least one attachment, each ≤ 200 KB | 60001 / 60004 |

Success:

```json
{ "CheckinUID": 17, "guests": [ { "uid": 14, "guestCode": "PC-ESCORT-0500", "attachments": [ … ] } ], "requestMessageID": 31, "hasErrors": false }
```

Here `guests[].uid` **is** the guest id — the opposite of `POST /checkin`.

### Editing an escort — `PUT /guest`

[`10_guest_put_edit_escort.json`](payloads/10_guest_put_edit_escort.json). Same
envelope and `GuestInfo`. Matching is on `DocumentNumber`: a guest whose document
already exists is updated in place rather than duplicated.

Same checks as `POST /guest` with two differences — it also rejects a cancelled
stay (40010), and its **50016 check is commented out**
([guest/routes.py:1415](../app/guest/routes.py#L1415)), which is what makes it an
edit rather than an add.

### What the API does *not* let you choose

`EscortTypeId` is **hard-coded to `2` (AdultEscort)** in every write path —
[checkin/routes.py:1100](../app/checkin/routes.py#L1100),
[checkin/routes.py:2149](../app/checkin/routes.py#L2149),
[guest/routes.py:838](../app/guest/routes.py#L838). There is no payload field for
it, so `1 ChildEscort` is never written, and `checkin.AdultEscortCount` /
`checkin.ChildEscortCount` are never populated — both are `null` on every row.
`GET /escorttype` still serves both values for the client's dropdown.

Likewise `AddEscortAction` appears in the overlap helpers
([checkin/routes.py:3928](../app/checkin/routes.py#L3928)) but no endpoint ever
passes it; the live callers pass `"CheckinRequest"` or `"BackdatedCheckinAction"`.
There is no `CheckinActionName` field to send.

### Escorts constrain everything that comes later

Check-out and room change both compare their timestamp against the **most
recently added `checkinguest` row** — i.e. the newest escort:

- `POST /roomchange` must be **after** that escort's check-in *and* check-out, or you get
  `The Room Change time should be greater than the Previous Escort's check-in Time at …`
- `POST /checkout` must likewise be after both, or
  `The Checkout time should be greater than the Previous Escort's Checkout Time at …`

So order your test timestamps strictly: check-in < escort check-in < room change
< escort check-out < check-out. `run_write_flow.ps1` does exactly this.

---

## Guest attachments

### `POST /guestattachment`

[`11_guestattachment_post.json`](payloads/11_guestattachment_post.json) — extra
documents for a guest already on an open stay.

```json
{
  "CheckinUID": "17",
  "GuestUID": "14",
  "MessageType": "GuestAttachmentRequest",
  "ClientUID": "Establishment101",
  "MessageUID": null,
  "CorrelationUID": "test-attachment-001",
  "Timestamp": "2026-08-04T09:00:00",
  "Attachments": [
    { "Id": 0, "UID": null, "AttachmentCode": "PC-DOC-EXTRA-0600", "Name": "Image_2.jpg", "Size": 160, "ContentBase64Encoded": "…" }
  ]
}
```

`GuestUID` is the **guest id** (`GET /guest` → `uid`), not the checkinguest id.
Codes: 40009, 40010, 40011, 50010 (no `GuestUID`), 60001 (no attachments),
60004 (over 200 KB).

Unlike the other endpoints this one **de-duplicates names**: a second
`Image_2.jpg` is stored as `Image_2_1.jpg`. Files land under
`BaseDirectoryPath\Attachments\…\<GuestId>\`, so this endpoint touches the
filesystem as well as the database.

### `GET /guestattachment`, `GET /guestdocumentimage`

No body. Row dumps. `guestdocumentimage` is currently broken — see the top.

---

## Guest check-out and main-guest handover

### `POST /guestcheckout` — one guest leaves, stay continues

[`12_guestcheckout_post_escort.json`](payloads/12_guestcheckout_post_escort.json)

```json
{
  "CheckinUID": "17",
  "GuestUID": "14",
  "CheckoutDateTime": "2026-08-04T10:00:00",
  "NewMainGuestUID": null,
  "MessageType": "GuestCheckoutRequest",
  "ClientUID": "Establishment101",
  "MessageUID": null,
  "CorrelationUID": "test-guestcheckout-001",
  "Timestamp": "2026-08-04T10:00:00"
}
```

Both `GuestUID` and `NewMainGuestUID` are **guest ids**. Rules: stay still open
(40011), `CheckoutDateTime` present (40014), not before that guest's check-in
(40032), not in the future (40004), guest not already checked out (50017).

### Main guest leaves — hand the stay over

[`13_guestcheckout_post_mainguest_handover.json`](payloads/13_guestcheckout_post_mainguest_handover.json)

Set `NewMainGuestUID` to the guest id of an escort who is staying:

```json
{
  "CheckinUID": "17",
  "GuestUID": "13",
  "CheckoutDateTime": "2026-08-04T10:15:00",
  "NewMainGuestUID": "14",
  "MessageType": "GuestCheckoutRequest",
  "…": "envelope"
}
```

The API then, in order: writes a `MainGuestChange` row and a
`MainGuestChangePOST` log; clears `IsMainGuest` on the outgoing guest and copies
the incoming guest's relationship onto them; sets `IsMainGuest` on the new main
guest and clears their relationship; snapshots a new `guestversion`; and only
then checks the departing guest out.

Two things to know:

- the handover is driven **entirely** by `NewMainGuestUID` — there is no separate
  main-guest-change endpoint (`GET /mainguestchange` is a read-only dump, 0 rows today)
- if the main guest leaves and you *don't* name a successor, this build does not
  raise 50018; it simply checks them out and leaves the stay with no main guest,
  which breaks later `guestversion` writes. Always send a successor.

### `GET /guestcheckout`, `GET /mainguestchange`

No body. Row dumps.

---

## Room change

### `POST /roomchange`

[`14_roomchange_post.json`](payloads/14_roomchange_post.json)

```json
{
  "CheckinUID": "17",
  "NewRoomNumber": "004",
  "EffectiveDate": "2026-08-04T09:30:00",
  "Comment": "payload collection - move the stay to another room",
  "MessageType": "RoomChangeRequest",
  "ClientUID": "Establishment101",
  "MessageUID": null,
  "CorrelationUID": "test-roomchange-001",
  "Timestamp": "2026-08-04T09:30:00"
}
```

The date field is **`EffectiveDate`**, not `EffectiveDateTime`. `NewRoomNumber`
must exist (80001) and be free (80003). `EffectiveDate` must not be in the
future, must be after the stay's check-in, after any previous room change, after
any main-guest change, and after the newest escort's check-in/check-out.

Frees the old room, flags the new one, and rewrites `checkin.RoomNumber`.
Returns a bare `{ "CheckinUID": 17 }`.

---

## Check-out

### `POST /checkout`

[`15_checkout_post.json`](payloads/15_checkout_post.json)

```json
{
  "CheckinUID": "17",
  "IsLateCheckout": false,
  "CheckoutDateTime": "2026-08-04T10:30:00",
  "Comment": "payload collection - close the stay",
  "MessageType": "CheckoutRequest",
  "ClientUID": "Establishment101",
  "MessageUID": null,
  "CorrelationUID": "test-checkout-001",
  "Timestamp": "2026-08-04T10:30:00"
}
```

Must be at or after every guest's check-in and every guest check-out already
recorded (40034), not in the future (40004), after any room change and any main
guest change, and after the newest escort's timestamps. 40010 if cancelled,
40011 if already checked out, 40039 if a house-use stay asks for late check-out.

Closes the stay, frees the room, stamps `CheckoutDate` on every guest still in
the room, and writes a `checkout` row with `CheckoutTypeId = 1`. Returns a bare
`{ "CheckinUID": 17 }`.

### `PUT /checkout`

[`16_checkout_put.json`](payloads/16_checkout_put.json) — adjusts a check-out
that has already happened. Requires the stay to be **inactive** (40031 if it is
still active — the mirror image of the POST). Same date rules, code 40032.

### `GET /checkout`

No body. All check-out rows.

---

## Check-in cancellation

### `POST /checkincancellation`

[`17_checkincancellation_post.json`](payloads/17_checkincancellation_post.json)

```json
{
  "CheckinUID": "17",
  "CancellationDateTime": "2026-08-04T09:00:00",
  "CancellationReasonCode": "UserError",
  "Comment": "payload collection - cancel a checkin created for testing",
  "MessageType": "CheckinCancellationRequest",
  "ClientUID": "Establishment101",
  "MessageUID": null,
  "CorrelationUID": "test-cancel-001",
  "Timestamp": "2026-08-04T09:00:00"
}
```

`CancellationReasonCode` is `Unhappy` or `UserError`. 40011 if already checked
out, 40010 if already cancelled, 40025 if the cancellation predates the
check-in, 40004 if in the future — and a free-text refusal if the current month
is later than the check-in's month ("The Cancel Checkout should be done in the
same month …").

Writes a `checkout` row with `CheckoutTypeId = 2` and a cancellation reason,
**frees the room**, and closes out every guest. Run it last, or on a check-in
you created for the test. Returns a bare `{ "CheckinUID": 17 }`.

---

## Monitoring

No payloads. All GET except the reset.

| Endpoint | Expect |
|---|---|
| `GET /ping` | `pong` |
| `GET /version` | version, PID, start time |
| `GET /health` | 200 `healthy: true`, or 503 with the failing check named |
| `GET /health?deep=false` | skips the database and filesystem probes |
| `GET /metrics` | counters + recent traffic |
| `POST /metrics/reset` | zeroes the counters (empty body) |
| `GET /routes` | all 50 URLs this build serves |
| `GET /status` | HTML dashboard |
| `GET /` | summary with links |

---

## Suggested test order

Each step feeds the next. Use free rooms so check-ins 6 and 8 are never
disturbed.

1. `GET /ping`, `GET /health` — up and connected
2. every [reference lookup](#reference-lookups-get) — read-only, and they prove the schema prefix is right
3. `GET /checkin` on Id `6`, `GET /guest` on Id `6` — reads of real records
4. `POST /checkin` on free room `003` — **capture `CheckinUID`**
5. `GET /checkin` on the new UID — confirm it landed
6. `POST /guest` — add an escort
7. `GET /guest` — collect the real **guest ids** for the next three steps
8. `POST /guestattachment` — second document for the escort
9. `POST /roomchange` to another free room, e.g. `004`
10. `POST /guestcheckout` — the escort leaves
11. `POST /checkout` — close the stay
12. `POST /checkincancellation` — on a throwaway check-in only
13. `GET /metrics` — every call above should be counted

Steps 1–3 and 13 are `check_all_reads.ps1`. Steps 4–11 are `run_write_flow.ps1`.
Steps 4–12 write to the database, and step 8 writes image files under
`BaseDirectoryPath`. Nothing is transactional across steps — clean up with SQL.

---

## Error codes

Grouped by the object they concern. Full text is in [API.md](API.md#error-codes).

| Range | Concerns | Examples seen in this build |
|---|---|---|
| 400xx | the check-in transaction | 40002 room missing · 40003 room inactive · 40004 date in future · 40005 no guests · 40006 no main guest · 40007 bad payment method · 40008 bad card number · 40009 no check-in · 40010 already cancelled · 40011 already checked out · 40014 bad check-out time · 40023 check-out time on a PUT · 40025 bad cancellation time · 40028 more than one main guest · 40031 stay still active · 40032/40034 check-out before a guest's dates · 40033 no guest at the transaction time · 40035–40038 house-use conflicts · 40039 house-use late check-out · 40050 room occupied |
| 500xx | a guest | 50001 first name / guest code · 50002 last name · 50005 nationality · 50006 residence country · 50007 birth date · 50008 visit purpose · 50009 relationship · 50010 guest not specified · 50011 mobile · 50013 birth place · 50014 guest check-in before the stay's · 50015 guest check-in in future · 50016 guest already on this stay · 50017 guest already checked out |
| 600xx | an attachment | 60001 none supplied · 60004 over 200 KB · 60006 document number · 60007 document type · 60008 issue date in future / missing "other" accessibility text · 60009 issue after expiry · 60010 issue country · 60011 expiry missing or expired · 60012 emirate required for `AE` · 60013 issue date missing |
| 800xx | a room change | 80001 new room missing · 80003 new room occupied |

Overlap failures do **not** carry a number — `errorMessages` is a free-text
sentence naming the conflicting check-in id and times.

---

## Gotchas

Things that cost time, all found in the route handlers:

- **`IsHouseUse` must be present and `false` on a normal check-in.** The guard
  reads `data.get('IsHouseUse', True)` — omit the key and a cash check-in is
  rejected with `40035 Check-in with house use flag does not require payment
  method` ([routes.py:288](../app/checkin/routes.py#L288)).
- **`ArabicName` is required by the shared validator, and must be Arabic-only.**
  `has_arabic_characters_only("")` returns `False`, so a missing or empty
  `ArabicName` fails on `POST`/`PUT /checkin`. It is then **never stored** — the
  API transliterates `FirstName`/`LastName` through `GOOGLE_TRANSLATOR_URL` into
  `ArabicFirstName`/`ArabicLastName`. The validator does *not* run on
  `GuestInfo`, so `POST /guest` accepts a payload without it.
- **`uid` means different things in different responses.** `POST /checkin` returns
  the **checkinguest** id; `POST /guest` and `GET /guest` return the **guest**
  id. `POST /guestattachment`, `POST /guestcheckout` and `NewMainGuestUID` all
  want the **guest** id — always take ids from `GET /guest`.
- **Guest identity is `DocumentNumber`.** Posting a guest whose document number
  already exists updates that guest instead of creating one, which is why the
  same person appears under several check-ins in the sample data. Reuse a
  document number on the *same* stay and you get 50016.
- **Some guest fields are read with `[]`, not `.get()`** — `GenderCode`, `Email`,
  `ResidenceCountryPhone`, `DocumentNumber`, `ResidenceCountryCode`,
  `CheckinDateTime`, `IsMainGuest` raise `KeyError` and surface as a **500**, not
  a tidy 400, when the key is missing. A 500 from `POST /checkin`: check for a
  missing key before anything else.
- **`POST /checkin` is not transactional.** It commits payment, check-in, guest,
  attachment, checkinguest, log and guestversion in separate steps; a failure
  part-way leaves orphans (that is what check-ins 14–16 are).
- **`Mobile` must be digits only**, and the stored `MobileCode` is derived from
  `ResidenceCountryCode`, not from the `Mobile` string.
- **`BirthPlace` must be letters with no spaces** — `Abu Dhabi` is rejected.
- **`PUT /checkin` uses `UID`; everything else uses `CheckinUID`.** And
  `POST /roomchange` uses `EffectiveDate`, not `EffectiveDateTime`.
- **`PUT /checkin` matches guests by `GuestId` across all check-ins**, newest
  first — it can edit the wrong stay's row for a repeat visitor.
- **Escort timestamps gate later transactions.** Room change and check-out are
  both compared against the newest `checkinguest` row; see
  [Escorts](#escorts-and-additional-guests).
- **`EscortTypeId` is always 2.** No payload can request `ChildEscort`.
- **A 200 from a reference lookup can still be a failure** — they catch their own
  database errors and return `{"error": "…"}` with status 200.
- **Dates have no timezone in the payload**, but responses come back in the
  server's local zone (`+05:30` here). The `timestamp` field is computed at
  *import* time, not per request, so it is the same on every response until the
  process restarts.
- **The 1.ID spec writes paths as `api/checkin/`.** This build serves them
  without the `api/` prefix. `GET /routes` is authoritative.

---

## What has been verified

Run on 2026-08-04 against the live instance.

| | |
|---|---|
| 14 reference lookups + 13 table dumps | ✅ executed — 26 return rows, `guestdocumentimage` errors |
| `/ping` `/version` `/health` `/metrics` `/routes` | ✅ executed — all OK, `/health` healthy, 50 routes. `/status`, `/`, `/favicon.ico` and `POST /metrics/reset` not run |
| `GET /checkin`, `GET /guest` with a body via `curl.exe` | ✅ executed — real data returned |
| `check_all_reads.ps1` | ✅ executed end to end |
| Every POST/PUT payload | ⚠️ **not executed.** Shapes come from the route handlers and the live code tables. They cannot succeed on this database until `guestdocumentimages` exists — see [the top of this file](#read-this-first-writes-are-broken-on-this-database). |

The write endpoints were left unrun deliberately: nothing in this database
changed while producing this document.
